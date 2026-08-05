from __future__ import annotations

"""Train matched AMD/NVDA 1m and 5m five-session unusual-call models."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

import lightgbm as lgb
import numpy as np


TARGET = "label_5d_net_return_pct"
FEATURE_PREFIXES = ("1min_", "5min_", "daily_", "symbol_is_")
MAX_DAILY_SELECTIONS = 1
PORTFOLIO_SLOTS = 5


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def feature_names(rows: list[Mapping[str, Any]]) -> list[str]:
    names = sorted(
        {
            name
            for row in rows
            for name in row
            if name.startswith(FEATURE_PREFIXES)
        }
    )
    if not names or any("label" in name or "future" in name for name in names):
        raise ValueError("invalid feature set")
    return names


def numeric(value: Any) -> float:
    if value is None:
        return np.nan
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan
    return result if np.isfinite(result) else np.nan


def matrix(rows: list[Mapping[str, Any]], names: list[str]) -> np.ndarray:
    return np.asarray(
        [[numeric(row.get(name)) for name in names] for row in rows],
        dtype=np.float32,
    )


def drawdown(rows: list[Mapping[str, Any]]) -> float | None:
    if not rows:
        return None
    by_exit: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_exit[str(row["label_5d_exit_market_date"])].append(float(row[TARGET]))
    equity = peak = 1.0
    worst = 0.0
    for market_date in sorted(by_exit):
        daily = sum(by_exit[market_date]) / PORTFOLIO_SLOTS / 100.0
        equity *= 1.0 + daily
        peak = max(peak, equity)
        worst = min(worst, equity / peak - 1.0)
    return worst * 100.0


def metrics(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"signals": 0, "decision_dates": 0}
    values = np.asarray([float(row[TARGET]) for row in rows])
    dates = {str(row["market_date"]) for row in rows}
    symbol_counts = {
        symbol: sum(str(row["symbol"]) == symbol for row in rows)
        for symbol in ("AMD", "NVDA")
    }
    rng = np.random.default_rng(260805)
    bootstrap = np.asarray(
        [
            float(np.mean(rng.choice(values, size=len(values), replace=True)))
            for _ in range(10000)
        ]
    )
    return {
        "signals": len(rows),
        "decision_dates": len(dates),
        "abstention_rate_pct": None,
        "mean_net_return_pct": round(float(np.mean(values)), 6),
        "median_net_return_pct": round(float(np.median(values)), 6),
        "win_rate_pct": round(float(np.mean(values > 0) * 100.0), 4),
        "bootstrap_mean_ci95_low_pct": round(
            float(np.percentile(bootstrap, 2.5)), 6
        ),
        "bootstrap_mean_ci95_high_pct": round(
            float(np.percentile(bootstrap, 97.5)), 6
        ),
        "target_2pct_rate_pct": round(float(np.mean(values >= 2) * 100.0), 4),
        "worst_net_return_pct": round(float(np.min(values)), 6),
        "capital_scaled_max_drawdown_pct": round(float(drawdown(rows)), 6),
        "symbol_counts": symbol_counts,
    }


def select(
    rows: list[dict[str, Any]],
    probabilities: np.ndarray,
    *,
    require_calls: bool,
) -> tuple[list[dict[str, Any]], int]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_dates = sorted({str(row["market_date"]) for row in rows})
    for source, probability in zip(rows, probabilities):
        row = {**source, "predicted_positive_probability": float(probability)}
        if probability <= 0.5:
            continue
        if require_calls and not (
            row.get("call_features_available") is True
            and int(row.get("call_activity_history_count") or 0) >= 10
            and row.get("call_volume_unusual") is True
        ):
            continue
        by_date[str(row["market_date"])].append(row)
    selected = []
    for market_date in all_dates:
        ranked = sorted(
            by_date.get(market_date, []),
            key=lambda row: (
                -float(row["predicted_positive_probability"]),
                str(row["symbol"]),
            ),
        )
        selected.extend(ranked[:MAX_DAILY_SELECTIONS])
    return selected, len(all_dates)


def train_one(panel: Path, output_root: Path) -> dict[str, Any]:
    rows = read_jsonl(panel)
    names = feature_names(rows)
    train = [
        row
        for row in rows
        if row["market_date"] < "2024-01-01"
        and row["label_5d_exit_market_date"] < "2024-01-01"
    ]
    validation = [
        row
        for row in rows
        if "2024-01-01" <= row["market_date"] < "2025-01-01"
        and row["label_5d_exit_market_date"] < "2025-01-01"
    ]
    refit = [
        row
        for row in rows
        if row["market_date"] < "2026-01-01"
        and row["label_5d_exit_market_date"] < "2026-01-01"
    ]
    test = [row for row in rows if row["market_date"] >= "2026-01-01"]
    if not all((train, validation, refit, test)):
        raise ValueError("fixed chronological partitions are incomplete")

    params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "learning_rate": 0.03,
        "num_leaves": 15,
        "max_depth": 5,
        "min_data_in_leaf": 40,
        "feature_fraction": 0.85,
        "bagging_fraction": 0.85,
        "bagging_freq": 1,
        "lambda_l1": 0.2,
        "lambda_l2": 1.0,
        "verbosity": -1,
        "seed": 260805,
        "feature_fraction_seed": 260805,
        "bagging_seed": 260805,
        "deterministic": True,
        "force_col_wise": True,
        "num_threads": 4,
    }
    fit = lgb.train(
        params,
        lgb.Dataset(
            matrix(train, names),
            label=np.asarray([float(row[TARGET]) > 0 for row in train]),
            feature_name=names,
        ),
        num_boost_round=800,
        valid_sets=[
            lgb.Dataset(
                matrix(validation, names),
                label=np.asarray([float(row[TARGET]) > 0 for row in validation]),
                feature_name=names,
                reference=None,
            )
        ],
        callbacks=[lgb.early_stopping(60, verbose=False)],
    )
    best_iteration = max(1, int(fit.best_iteration))
    final = lgb.train(
        params,
        lgb.Dataset(
            matrix(refit, names),
            label=np.asarray([float(row[TARGET]) > 0 for row in refit]),
            feature_name=names,
        ),
        num_boost_round=best_iteration,
    )
    probabilities = final.predict(matrix(test, names), num_iteration=best_iteration)
    baseline, baseline_dates = select(test, probabilities, require_calls=False)
    calls, call_dates = select(test, probabilities, require_calls=True)
    call_metrics = metrics(calls)
    call_eligible_dates = len(
        {
            row["market_date"]
            for row in test
            if row.get("call_features_available") is True
            and int(row.get("call_activity_history_count") or 0) >= 10
        }
    )
    call_metrics["eligible_call_dates"] = call_eligible_dates
    call_metrics["abstention_rate_pct"] = round(
        (1.0 - len({row["market_date"] for row in calls}) / max(call_eligible_dates, 1))
        * 100.0,
        4,
    )
    baseline_metrics = metrics(baseline)
    baseline_metrics["abstention_rate_pct"] = round(
        (1.0 - len({row["market_date"] for row in baseline}) / baseline_dates)
        * 100.0,
        4,
    )
    status = (
        "historical_holdout_promising_not_promoted"
        if call_metrics["signals"] >= 20
        and call_metrics["mean_net_return_pct"] > 0
        and call_metrics["win_rate_pct"] >= 55
        else "research_hold"
    )
    output_root.mkdir(parents=True, exist_ok=True)
    stem = panel.stem.replace("_five_session_panel", "")
    model_path = output_root / f"{stem}_technical_model.txt"
    final.save_model(str(model_path))
    selections_path = output_root / f"{stem}_historical_call_selections.jsonl"
    with selections_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in calls:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    report = {
        "status": status,
        "research_only": True,
        "execution_enabled": False,
        "symbols": ["AMD", "NVDA"],
        "resolution": str(rows[0]["resolution"]),
        "horizon_sessions": 5,
        "feature_count": len(names),
        "feature_names": names,
        "partitions": {
            "initial_train": {
                "rows": len(train),
                "first": min(row["market_date"] for row in train),
                "last": max(row["market_date"] for row in train),
            },
            "early_stopping_validation": {
                "rows": len(validation),
                "first": min(row["market_date"] for row in validation),
                "last": max(row["market_date"] for row in validation),
            },
            "refit_pretest": {
                "rows": len(refit),
                "first": min(row["market_date"] for row in refit),
                "last": max(row["market_date"] for row in refit),
            },
            "historical_holdout": {
                "rows": len(test),
                "first": min(row["market_date"] for row in test),
                "last": max(row["market_date"] for row in test),
            },
        },
        "best_iteration": best_iteration,
        "baseline_positive_top_one": baseline_metrics,
        "unusual_call_positive_top_one": call_metrics,
        "selection_contract": (
            "at most one of AMD/NVDA; predicted probability must exceed 0.50; "
            "exact call history >=10; call z-score >=3; otherwise abstain"
        ),
        "panel": str(panel),
        "panel_sha256": sha256(panel),
        "model": str(model_path),
        "model_sha256": sha256(model_path),
        "selections": str(selections_path),
        "selections_sha256": sha256(selections_path),
        "limitations": [
            "The unusual-call holdout covers only 2026-01 through 2026-07.",
            "This is historical held-out evidence, not prospective evidence.",
            "Two-symbol concentration prevents broad-universe diversification.",
        ],
    }
    report_path = output_root / f"{stem}_training_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    reports = []
    for resolution in ("1min", "5min"):
        panel = (
            args.panel_root
            / f"amd_nvda_{resolution}_five_session_panel.jsonl"
        )
        reports.append(train_one(panel, args.output_root))
    comparison = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "models": reports,
    }
    comparison_path = args.output_root / "comparison.json"
    comparison_path.write_text(
        json.dumps(comparison, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    main()
