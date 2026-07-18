from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import lightgbm as lgb
import numpy as np

from alientai_v2.features.insider_purchase_features import safe_float


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def date_from_ms(value: int) -> date:
    return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc).date()


def build_matrix(rows: Sequence[Mapping[str, Any]], feature_names: Sequence[str]) -> np.ndarray:
    columns: List[np.ndarray] = []
    for name in feature_names:
        if name.startswith("label_"):
            raise ValueError("future outcome labels cannot be model features")
        if name.endswith("__missing"):
            source = name[: -len("__missing")]
            columns.append(np.asarray([row.get(source) is None for row in rows], dtype=np.float32))
        else:
            columns.append(np.asarray([safe_float(row.get(name)) for row in rows], dtype=np.float32))
    return np.column_stack(columns).astype(np.float32)


def chronological_partitions(
    rows: Sequence[Mapping[str, Any]], train_cutoff_ms: int, validation_cutoff_ms: int,
    embargo_calendar_days: int,
) -> Tuple[List[Mapping[str, Any]], List[Mapping[str, Any]]]:
    train_cutoff = date_from_ms(train_cutoff_ms)
    validation_cutoff = date_from_ms(validation_cutoff_ms)
    calibration_start = train_cutoff + timedelta(days=embargo_calendar_days)
    calibration_end = validation_cutoff - timedelta(days=embargo_calendar_days)
    test_start = validation_cutoff + timedelta(days=embargo_calendar_days)
    calibration = []
    test = []
    for row in rows:
        day = date.fromisoformat(str(row["market_date"]))
        if calibration_start <= day <= calibration_end:
            calibration.append(row)
        elif day >= test_start:
            test.append(row)
    return calibration, test


def quantile_calibration(
    scores: np.ndarray, labels: np.ndarray, bin_count: int = 20,
) -> List[Dict[str, float]]:
    if len(scores) != len(labels) or not len(scores):
        raise ValueError("scores and labels must be non-empty and aligned")
    order = np.argsort(scores)
    groups = np.array_split(order, min(max(2, bin_count), len(order)))
    bins = [
        {
            "max_score": float(np.max(scores[group])),
            "empirical_probability": float(np.mean(labels[group])),
            "count": int(len(group)),
        }
        for group in groups if len(group)
    ]
    # Pool adjacent violators so calibrated probability never falls as score rises.
    blocks: List[Dict[str, float]] = []
    for item in bins:
        blocks.append(dict(item))
        while len(blocks) >= 2 and blocks[-2]["empirical_probability"] > blocks[-1]["empirical_probability"]:
            right = blocks.pop()
            left = blocks.pop()
            count = int(left["count"] + right["count"])
            blocks.append({
                "max_score": right["max_score"],
                "empirical_probability": (
                    left["empirical_probability"] * left["count"]
                    + right["empirical_probability"] * right["count"]
                ) / count,
                "count": count,
            })
    return blocks


def apply_calibration(scores: np.ndarray, bins: Sequence[Mapping[str, float]]) -> np.ndarray:
    edges = np.asarray([item["max_score"] for item in bins], dtype=float)
    values = np.asarray([item["empirical_probability"] for item in bins], dtype=float)
    locations = np.searchsorted(edges, scores, side="left")
    return values[np.minimum(locations, len(values) - 1)]


def non_overlapping(rows: Sequence[Mapping[str, Any]], hold_calendar_days: int = 7) -> List[Mapping[str, Any]]:
    latest_exit: Dict[str, date] = {}
    selected = []
    for row in sorted(rows, key=lambda item: (str(item["market_date"]), -float(item["raw_score"]))):
        symbol = str(row["symbol"])
        day = date.fromisoformat(str(row["market_date"]))
        if day < latest_exit.get(symbol, date.min):
            continue
        selected.append(row)
        latest_exit[symbol] = day + timedelta(days=hold_calendar_days)
    return selected


def max_drawdown(returns_pct: Iterable[float]) -> float:
    equity = peak = 1.0
    worst = 0.0
    for value in returns_pct:
        equity *= 1.0 + float(value) / 100.0
        peak = max(peak, equity)
        worst = min(worst, (equity / peak - 1.0) * 100.0)
    return worst


def selection_metrics(rows: Sequence[Mapping[str, Any]], round_trip_cost_pct: float) -> Dict[str, Any]:
    if not rows:
        return {"signals": 0}
    net = np.asarray([safe_float(row["label_forward_return_5d_pct"]) - round_trip_cost_pct for row in rows])
    labels = np.asarray([safe_float(row["label_forward_return_5d_pct"]) >= 10.0 for row in rows])
    by_exit: Dict[str, List[float]] = defaultdict(list)
    for row, value in zip(rows, net):
        by_exit[str(row.get("future_market_date") or row["market_date"])].append(float(value))
    cohort_returns = [float(np.mean(by_exit[key])) for key in sorted(by_exit)]
    return {
        "signals": len(rows),
        "symbols": len({str(row["symbol"]) for row in rows}),
        "exceptional_winner_rate": round(float(np.mean(labels)), 6),
        "mean_net_return_pct": round(float(np.mean(net)), 6),
        "median_net_return_pct": round(float(np.median(net)), 6),
        "win_rate_after_cost": round(float(np.mean(net > 0)), 6),
        "worst_trade_net_return_pct": round(float(np.min(net)), 6),
        "cohort_exit_date_count": len(cohort_returns),
        "approximate_cohort_max_drawdown_pct": round(max_drawdown(cohort_returns), 6),
    }


def evaluate_slices(
    rows: Sequence[Mapping[str, Any]], round_trip_cost_pct: float,
) -> List[Dict[str, Any]]:
    order = sorted(rows, key=lambda row: float(row["raw_score"]), reverse=True)
    output = []
    for fraction in (0.001, 0.0025, 0.005, 0.01):
        count = max(1, int(len(order) * fraction))
        chosen = non_overlapping(order[:count])
        output.append({"selection": f"top_{fraction:.4f}", **selection_metrics(chosen, round_trip_cost_pct)})
    for threshold in (0.70, 0.75, 0.80):
        chosen = non_overlapping([row for row in rows if float(row["raw_score"]) >= threshold])
        output.append({"selection": f"raw_score_gte_{threshold:.2f}", **selection_metrics(chosen, round_trip_cost_pct)})
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate matched-winner scores on the natural full universe.")
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--training-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--embargo-calendar-days", type=int, default=12)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()

    rows = read_jsonl(args.rows)
    training_report = json.loads(args.training_report.read_text(encoding="utf-8"))
    model = lgb.Booster(model_file=str(args.model))
    calibration_rows, test_rows = chronological_partitions(
        rows,
        int(training_report["split"]["train_cutoff_datetime_ms"]),
        int(training_report["split"]["validation_cutoff_datetime_ms"]),
        args.embargo_calendar_days,
    )
    if not calibration_rows or not test_rows:
        raise ValueError("full-universe calibration and unseen test rows are required")
    calibration_scores = model.predict(build_matrix(calibration_rows, model.feature_name()))
    calibration_labels = np.asarray([
        safe_float(row["label_forward_return_5d_pct"]) >= 10.0 for row in calibration_rows
    ], dtype=np.int32)
    bins = quantile_calibration(calibration_scores, calibration_labels)
    test_scores = model.predict(build_matrix(test_rows, model.feature_name()))
    calibrated = apply_calibration(test_scores, bins)
    scored_test = [
        {**row, "raw_score": float(score), "calibrated_probability": float(probability)}
        for row, score, probability in zip(test_rows, test_scores, calibrated)
    ]
    base_rate = float(np.mean([safe_float(row["label_forward_return_5d_pct"]) >= 10.0 for row in test_rows]))
    report = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "warning": "Cohort drawdown assigns each five-day return to its exit date; it is not a mark-to-market portfolio simulation.",
        "natural_universe_test_rows": len(test_rows),
        "natural_exceptional_winner_base_rate": round(base_rate, 6),
        "calibration_rows": len(calibration_rows),
        "calibration_bins": bins,
        "round_trip_cost_pct": args.round_trip_cost_pct,
        "test_slices": evaluate_slices(scored_test, args.round_trip_cost_pct),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
