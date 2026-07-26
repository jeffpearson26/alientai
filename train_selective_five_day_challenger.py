"""Train the isolated five-day LightGBM challenger from existing local data."""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.research.five_day_open_close_labels import (
    build_next_open_five_close_labels,
)
from alientai_v2.research.selective_five_day_panel import (
    build_selective_five_day_panel,
)
from evaluate_matched_winner_full_universe import (
    apply_calibration,
    quantile_calibration,
)


BUILD = "ALIENTAI_SELECTIVE_FIVE_DAY_CHALLENGER_V1"
FIXED_POLICY = {
    "minimum_profit_probability": 0.60,
    "minimum_large_move_probability": 0.30,
    "minimum_expected_net_return_pct": 0.75,
    "minimum_lower_quantile_net_return_pct": -5.0,
    "round_trip_cost_pct": 0.25,
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def daily_archive_sha256(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(directory.glob("*_schwab_1d_max.csv"), key=lambda item: item.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(file_sha256(path).encode("ascii"))
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def safe_float(value: Any) -> float:
    if value is None:
        return np.nan
    if isinstance(value, bool):
        return float(value)
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan
    return result if np.isfinite(result) else np.nan


def sanitized_feature_row(row: Mapping[str, Any]) -> dict[str, Any]:
    result = {
        "symbol": str(row.get("symbol") or "").upper().strip(),
        "market_date": str(row.get("market_date") or ""),
        "as_of_utc": row.get("as_of_utc"),
        "decision_cutoff_utc": row.get("as_of_utc"),
    }
    for name, value in row.items():
        if name.startswith("technical_") or name.startswith("option_"):
            result[name] = value
    return result


def local_candle_files(directory: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in directory.glob("*_schwab_1d_max.csv"):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            first = next(csv.DictReader(handle), None)
        symbol = str((first or {}).get("symbol") or "").upper().strip()
        if symbol:
            result[symbol] = path
    return result


def read_candles(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append({
                "date": row.get("date"),
                "open": safe_float(row.get("open")),
                "close": safe_float(row.get("close")),
            })
    return rows


def materialize_panel(
    source_rows: Sequence[Mapping[str, Any]],
    daily_directory: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    features = [sanitized_feature_row(row) for row in source_rows]
    features_by_key = {
        (str(row["symbol"]), str(row["market_date"])): row for row in features
    }
    if len(features_by_key) != len(features):
        raise ValueError("source panel contains duplicate symbol/date rows")
    files = local_candle_files(daily_directory)
    labels_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    symbols_requested = sorted({key[0] for key in features_by_key})
    for symbol in symbols_requested:
        path = files.get(symbol)
        if path is None:
            continue
        for row in build_next_open_five_close_labels(
            symbol,
            read_candles(path),
            round_trip_cost_pct=float(FIXED_POLICY["round_trip_cost_pct"]),
            large_move_target_pct=2.0,
        ):
            key = (symbol, str(row["decision_date"]))
            if key in features_by_key:
                labels_by_key[key] = row

    common = sorted(set(features_by_key) & set(labels_by_key))
    joined = build_selective_five_day_panel(
        [features_by_key[key] for key in common],
        [labels_by_key[key] for key in common],
    )
    return joined, {
        "source_rows": len(source_rows),
        "source_symbols": len(symbols_requested),
        "local_daily_symbols": len(files),
        "joined_rows": len(joined),
        "excluded_without_local_label": len(features_by_key) - len(common),
    }


def feature_names(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    names = sorted({
        name for row in rows for name in row
        if name.startswith("technical_") or name.startswith("option_")
    })
    return names + [f"{name}__missing" for name in names]


def matrix(rows: Sequence[Mapping[str, Any]], names: Sequence[str]) -> np.ndarray:
    columns = []
    for name in names:
        if name.endswith("__missing"):
            source = name[:-9]
            columns.append(np.asarray([safe_float(row.get(source)) != safe_float(row.get(source)) for row in rows], dtype=np.float32))
        else:
            columns.append(np.asarray([safe_float(row.get(name)) for row in rows], dtype=np.float32))
    return np.column_stack(columns).astype(np.float32)


def chronological_split(
    rows: Sequence[Mapping[str, Any]],
    train_fraction: float = 0.60,
    validation_fraction: float = 0.20,
    embargo_days: int = 12,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    days = sorted({date.fromisoformat(str(row["market_date"])) for row in rows})
    if len(days) < 20:
        raise ValueError("not enough unique dates for chronological split")
    train_cutoff = days[max(0, int(len(days) * train_fraction) - 1)]
    validation_cutoff = days[max(1, int(len(days) * (train_fraction + validation_fraction)) - 1)]
    validation_start = train_cutoff + timedelta(days=embargo_days)
    test_start = validation_cutoff + timedelta(days=embargo_days)
    train = []
    validation = []
    test = []
    for index, row in enumerate(rows):
        day = date.fromisoformat(str(row["market_date"]))
        if day <= train_cutoff:
            train.append(index)
        elif validation_start <= day <= validation_cutoff:
            validation.append(index)
        elif day >= test_start:
            test.append(index)
    if not train or not validation or not test:
        raise ValueError("chronological split produced an empty partition")
    return (
        np.asarray(train, dtype=np.int64),
        np.asarray(validation, dtype=np.int64),
        np.asarray(test, dtype=np.int64),
        {
            "train_end": train_cutoff.isoformat(),
            "validation_start": validation_start.isoformat(),
            "validation_end": validation_cutoff.isoformat(),
            "test_start": test_start.isoformat(),
            "embargo_calendar_days": embargo_days,
        },
    )


def train_booster(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_validation: np.ndarray,
    y_validation: np.ndarray,
    names: Sequence[str],
    *,
    objective: str,
    metric: str,
    seed: int,
    alpha: float | None = None,
) -> lgb.Booster:
    params: dict[str, Any] = {
        "objective": objective,
        "metric": metric,
        "learning_rate": 0.03,
        "num_leaves": 31,
        "min_data_in_leaf": 100,
        "feature_fraction": 0.80,
        "bagging_fraction": 0.80,
        "bagging_freq": 5,
        "lambda_l1": 2.0,
        "lambda_l2": 6.0,
        "verbosity": -1,
        "seed": seed,
        "force_col_wise": True,
    }
    if alpha is not None:
        params["alpha"] = alpha
    train = lgb.Dataset(x_train, label=y_train, feature_name=list(names))
    validation = lgb.Dataset(x_validation, label=y_validation, reference=train, feature_name=list(names))
    return lgb.train(
        params,
        train,
        num_boost_round=1200,
        valid_sets=[validation],
        valid_names=["validation"],
        callbacks=[lgb.early_stopping(75), lgb.log_evaluation(50)],
    )


def outcome_metrics(net_returns: np.ndarray) -> dict[str, Any]:
    if not len(net_returns):
        return {"signals": 0}
    ordered = np.asarray(net_returns, dtype=float)
    equity = peak = 1.0
    worst_drawdown = 0.0
    for value in ordered:
        equity *= 1.0 + value / 100.0
        peak = max(peak, equity)
        worst_drawdown = min(worst_drawdown, (equity / peak - 1.0) * 100.0)
    return {
        "signals": int(len(ordered)),
        "mean_net_return_pct": float(np.mean(ordered)),
        "median_net_return_pct": float(np.median(ordered)),
        "win_rate_after_cost": float(np.mean(ordered > 0.0)),
        "fifth_percentile_net_return_pct": float(np.quantile(ordered, 0.05)),
        "worst_trade_net_return_pct": float(np.min(ordered)),
        "approximate_cohort_max_drawdown_pct": float(worst_drawdown),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-panel",
        default=r"D:\AlientAI\Data\FINRA_Short_Interest\features\natural_options_finra_research_panel_2026.jsonl",
    )
    parser.add_argument("--daily-dir", default="data_v2/sp500_daily_schwab_max_history")
    parser.add_argument("--output-dir", default="data_v2/selective_five_day_challenger_training")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    input_path = Path(args.input_panel).resolve()
    daily_path = (root / args.daily_dir).resolve()
    source_rows = read_jsonl(input_path)
    rows, coverage = materialize_panel(source_rows, daily_path)
    names = feature_names(rows)
    x = matrix(rows, names)
    positive = np.asarray([int(row["label_positive_net_return"]) for row in rows], dtype=np.int32)
    large = np.asarray([int(row["label_large_move"]) for row in rows], dtype=np.int32)
    net = np.asarray([float(row["net_return_pct"]) for row in rows], dtype=np.float32)
    train_idx, validation_idx, test_idx, split = chronological_split(rows)

    positive_model = train_booster(x[train_idx], positive[train_idx], x[validation_idx], positive[validation_idx], names, objective="binary", metric="binary_logloss", seed=41)
    large_model = train_booster(x[train_idx], large[train_idx], x[validation_idx], large[validation_idx], names, objective="binary", metric="binary_logloss", seed=42)
    expected_model = train_booster(x[train_idx], net[train_idx], x[validation_idx], net[validation_idx], names, objective="huber", metric="l1", seed=43)
    lower_model = train_booster(x[train_idx], net[train_idx], x[validation_idx], net[validation_idx], names, objective="quantile", metric="quantile", seed=44, alpha=0.10)

    validation_positive_raw = positive_model.predict(x[validation_idx])
    validation_large_raw = large_model.predict(x[validation_idx])
    positive_bins = quantile_calibration(validation_positive_raw, positive[validation_idx])
    large_bins = quantile_calibration(validation_large_raw, large[validation_idx])

    test_positive = apply_calibration(positive_model.predict(x[test_idx]), positive_bins)
    test_large = apply_calibration(large_model.predict(x[test_idx]), large_bins)
    test_expected = expected_model.predict(x[test_idx])
    test_lower = lower_model.predict(x[test_idx])
    selected = (
        (test_positive >= FIXED_POLICY["minimum_profit_probability"])
        & (test_large >= FIXED_POLICY["minimum_large_move_probability"])
        & (test_expected >= FIXED_POLICY["minimum_expected_net_return_pct"])
        & (test_lower >= FIXED_POLICY["minimum_lower_quantile_net_return_pct"])
    )
    chosen_indices = test_idx[selected]
    chosen_returns = net[chosen_indices]
    test_days = [rows[int(index)]["market_date"] for index in chosen_indices]

    output = (root / args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    models = {
        "positive_classifier.txt": positive_model,
        "large_move_classifier.txt": large_model,
        "expected_net_return_regressor.txt": expected_model,
        "lower_quantile_net_return_regressor.txt": lower_model,
    }
    for filename, model in models.items():
        model.save_model(str(output / filename), num_iteration=model.best_iteration)

    report = {
        "build": BUILD,
        "status": "RESEARCH_HOLD",
        "research_only": True,
        "execution_enabled": False,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "coverage": coverage,
        "input_artifacts": {
            "source_panel_path": str(input_path),
            "source_panel_sha256": file_sha256(input_path),
            "daily_archive_path": str(daily_path),
            "daily_archive_sha256": daily_archive_sha256(daily_path),
        },
        "feature_count": len(names),
        "features": names,
        "split": split,
        "partition_rows": {
            "train": int(len(train_idx)),
            "validation": int(len(validation_idx)),
            "untouched_test": int(len(test_idx)),
        },
        "fixed_policy_before_test": FIXED_POLICY,
        "validation_calibration": {
            "positive_bins": positive_bins,
            "large_move_bins": large_bins,
        },
        "untouched_test": {
            "universe_positive_rate": float(np.mean(positive[test_idx])),
            "universe_large_move_rate": float(np.mean(large[test_idx])),
            "universe_mean_net_return_pct": float(np.mean(net[test_idx])),
            "selected_distinct_dates": len(set(test_days)),
            "selected_outcomes": outcome_metrics(chosen_returns),
        },
        "promotion_status": "RESEARCH_HOLD",
        "promotion_blockers": [
            "first observed historical challenger test",
            "Transformer disagreement component not trained",
            "prospective evidence not collected",
            "paper/live execution remains disabled",
        ],
        "model_artifacts": {
            filename: {
                "path": str(output / filename),
                "sha256": file_sha256(output / filename),
            }
            for filename in models
        },
    }
    (output / "training_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
