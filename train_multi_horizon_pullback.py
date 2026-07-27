from __future__ import annotations

"""Train research-only recovery models for intact uptrends experiencing dips."""

import argparse
import csv
from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np

from alientai_v2.research.multi_horizon_pullback import build_pullback_features
from audit_selective_challenger_validation import binary_auc


FEATURES = [
    f"pullback_trend_slope_{horizon}d_pct_per_day" for horizon in (20, 63, 126)
] + [
    f"pullback_distance_from_sma_{horizon}d_pct" for horizon in (20, 63, 126)
] + [
    f"pullback_from_{horizon}d_high_pct" for horizon in (5, 10, 20)
] + [
    "pullback_return_1d_pct",
    "pullback_return_5d_pct",
    "pullback_volatility_20d_pct",
    "pullback_setup_eligible",
]


def read_candles(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: str(row.get("date") or ""))
    return rows


def net_return(rows: list[dict[str, Any]], index: int, horizon: int, cost: float) -> float | None:
    if index + horizon >= len(rows):
        return None
    days = [date.fromisoformat(str(rows[position]["date"])) for position in range(index, index + horizon + 1)]
    if any((days[position] - days[position - 1]).days > 5 for position in range(1, len(days))):
        return None
    try:
        entry = float(rows[index + 1]["open"])
        exit_ = float(rows[index + horizon]["close"])
    except (KeyError, TypeError, ValueError):
        return None
    if entry <= 0 or exit_ <= 0:
        return None
    return (exit_ / entry - 1.0) * 100.0 - cost


def build_examples(
    symbol: str,
    candles: list[dict[str, Any]],
    *,
    step_days: int,
    round_trip_cost_pct: float,
) -> list[dict[str, Any]]:
    examples = []
    for index in range(125, len(candles) - 5, step_days):
        try:
            features = build_pullback_features(candles[index - 125:index + 1])
        except ValueError:
            # Provider archives can contain isolated zero/missing prices.
            # Exclude the affected point-in-time window; never coerce it to a
            # valid price or label it as a losing setup.
            continue
        # The model's universe is an intact multi-horizon uptrend. Dip depth
        # remains continuous; the hard setup flag is one feature, not the label.
        if not features["pullback_all_trend_slopes_positive"]:
            continue
        if features["pullback_distance_from_sma_126d_pct"] <= 0.0:
            continue
        two = net_return(candles, index, 2, round_trip_cost_pct)
        five = net_return(candles, index, 5, round_trip_cost_pct)
        if two is None or five is None:
            continue
        examples.append({
            "symbol": symbol,
            "market_date": str(candles[index]["date"]),
            **{name: features[name] for name in FEATURES},
            "net_return_2d_pct": two,
            "net_return_5d_pct": five,
        })
    return examples


def split_indices(rows: list[dict[str, Any]], embargo_days: int = 12):
    days = sorted({date.fromisoformat(row["market_date"]) for row in rows})
    train_end = days[int(len(days) * 0.60) - 1]
    validation_end = days[int(len(days) * 0.80) - 1]
    validation_start = train_end + timedelta(days=embargo_days)
    test_start = validation_end + timedelta(days=embargo_days)
    train = np.asarray([i for i, row in enumerate(rows) if date.fromisoformat(row["market_date"]) <= train_end])
    validation = np.asarray([i for i, row in enumerate(rows) if validation_start <= date.fromisoformat(row["market_date"]) <= validation_end])
    test = np.asarray([i for i, row in enumerate(rows) if date.fromisoformat(row["market_date"]) >= test_start])
    return train, validation, test, {
        "train_end": train_end.isoformat(),
        "validation_start": validation_start.isoformat(),
        "validation_end": validation_end.isoformat(),
        "test_start": test_start.isoformat(),
        "embargo_calendar_days": embargo_days,
    }


def outcome_metrics(values: np.ndarray) -> dict[str, Any]:
    if not len(values):
        return {"rows": 0}
    return {
        "rows": int(len(values)),
        "mean_net_return_pct": float(np.mean(values)),
        "median_net_return_pct": float(np.median(values)),
        "win_rate_pct": float(np.mean(values > 0.0) * 100.0),
        "fifth_percentile_net_return_pct": float(np.quantile(values, 0.05)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--daily-dir", type=Path, default=Path("data_v2/sp500_daily_schwab_max_history"))
    parser.add_argument("--output-dir", type=Path, default=Path("data_v2/multi_horizon_pullback_training"))
    parser.add_argument("--step-days", type=int, default=5)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    rows = []
    summaries = []
    for path in sorted((root / args.daily_dir).glob("*_schwab_1d_max.csv")):
        candles = read_candles(path)
        symbol = str(candles[0].get("symbol") or path.name.split("_")[0]).upper() if candles else ""
        examples = build_examples(
            symbol, candles, step_days=args.step_days,
            round_trip_cost_pct=args.round_trip_cost_pct,
        )
        rows.extend(examples)
        summaries.append({"symbol": symbol, "candles": len(candles), "examples": len(examples)})
    if not rows:
        raise RuntimeError("no pullback examples were built")
    rows.sort(key=lambda row: (row["market_date"], row["symbol"]))
    x = np.asarray([
        [float(row[name]) if not isinstance(row[name], bool) else float(row[name]) for name in FEATURES]
        for row in rows
    ], dtype=np.float32)
    train, validation, test, split = split_indices(rows)
    output = root / args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "build": "ALIENTAI_MULTI_HORIZON_PULLBACK_V1",
        "status": "RESEARCH_HOLD",
        "research_only": True,
        "execution_enabled": False,
        "features": FEATURES,
        "rows": len(rows),
        "symbols": len({row["symbol"] for row in rows}),
        "step_days": args.step_days,
        "round_trip_cost_pct": args.round_trip_cost_pct,
        "split": split,
        "partition_rows": {"train": len(train), "validation": len(validation), "untouched_test": len(test)},
        "horizons": {},
    }
    for horizon in (2, 5):
        returns = np.asarray([row[f"net_return_{horizon}d_pct"] for row in rows], dtype=np.float32)
        labels = (returns > 0.0).astype(np.int32)
        train_data = lgb.Dataset(x[train], label=labels[train], feature_name=FEATURES)
        validation_data = lgb.Dataset(x[validation], label=labels[validation], reference=train_data)
        model = lgb.train(
            {
                "objective": "binary", "metric": "binary_logloss", "learning_rate": 0.03,
                "num_leaves": 31, "min_data_in_leaf": 100, "feature_fraction": 0.85,
                "bagging_fraction": 0.85, "bagging_freq": 1, "verbosity": -1, "seed": 210 + horizon,
            },
            train_data,
            num_boost_round=500,
            valid_sets=[validation_data],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )
        validation_scores = model.predict(x[validation])
        cutoff = float(np.quantile(validation_scores, 0.95, method="higher"))
        test_scores = model.predict(x[test])
        validation_selected = validation[validation_scores >= cutoff]
        test_selected = test[test_scores >= cutoff]
        setup_validation = validation[np.asarray([bool(rows[i]["pullback_setup_eligible"]) for i in validation])]
        setup_test = test[np.asarray([bool(rows[i]["pullback_setup_eligible"]) for i in test])]
        model_path = output / f"pullback_{horizon}day_classifier.txt"
        model.save_model(str(model_path))
        report["horizons"][f"{horizon}_day"] = {
            "validation_auc": binary_auc(labels[validation], validation_scores),
            "untouched_test_auc": binary_auc(labels[test], test_scores),
            "validation_top5_score_cutoff": cutoff,
            "validation_top5": outcome_metrics(returns[validation_selected]),
            "untouched_test_frozen_cutoff": outcome_metrics(returns[test_selected]),
            "rule_only_validation": outcome_metrics(returns[setup_validation]),
            "rule_only_untouched_test": outcome_metrics(returns[setup_test]),
            "model_path": str(model_path.resolve()),
        }
    (output / "training_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output / "symbol_summary.json").write_text(json.dumps(summaries, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
