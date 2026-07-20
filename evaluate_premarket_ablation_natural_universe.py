from __future__ import annotations

"""Calibrate and evaluate premarket ablation models on the natural universe."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from evaluate_matched_winner_full_universe import (
    apply_calibration,
    build_matrix,
    chronological_partitions,
    evaluate_slices,
    quantile_calibration,
    read_jsonl,
)
from train_matched_winner_premarket_ablation import join_feature_rows, join_open_entry_labels


def natural_promotion_gate(evaluations: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    by_name = {str(item.get("name")): item for item in evaluations}
    baseline = by_name.get("technical_only")
    combined = by_name.get("technical_plus_premarket")
    checks = []
    for fraction in ("top_0.0010", "top_0.0025", "top_0.0050", "top_0.0100"):
        base_slice = next((row for row in (baseline or {}).get("test_slices", []) if row.get("selection") == fraction), None)
        combo_slice = next((row for row in (combined or {}).get("test_slices", []) if row.get("selection") == fraction), None)
        if base_slice is None or combo_slice is None:
            checks.append({"selection": fraction, "passed": False, "reason": "required slice missing"})
            continue
        conditions = {
            "minimum_signals": int(combo_slice.get("signals") or 0) >= 30,
            "exceptional_rate_improved": float(combo_slice["exceptional_winner_rate"]) > float(base_slice["exceptional_winner_rate"]),
            "mean_net_return_improved": float(combo_slice["mean_net_return_pct"]) > float(base_slice["mean_net_return_pct"]),
            "median_net_return_positive": float(combo_slice["median_net_return_pct"]) > 0.0,
            "drawdown_not_worse": (
                float(combo_slice["approximate_cohort_max_drawdown_pct"])
                >= float(base_slice["approximate_cohort_max_drawdown_pct"])
            ),
        }
        checks.append({
            "selection": fraction, "passed": all(conditions.values()),
            "conditions": conditions, "baseline": base_slice, "combined": combo_slice,
        })
    passing = [item for item in checks if item.get("passed")]
    return {
        "status": "NATURAL_UNIVERSE_PASS" if passing else "NATURAL_UNIVERSE_HOLD",
        "execution_enabled": False, "passing_slice_count": len(passing), "checks": checks,
        "note": "A pass permits prospective shadow testing only and never enables trading.",
    }


def evaluate_model(
    experiment: Mapping[str, Any], rows: Sequence[Mapping[str, Any]],
    calibration_rows: Sequence[Mapping[str, Any]], test_rows: Sequence[Mapping[str, Any]],
    round_trip_cost_pct: float,
) -> Dict[str, Any]:
    model = lgb.Booster(model_file=str(experiment["model_path"]))
    feature_names = model.feature_name()
    calibration_scores = model.predict(build_matrix(calibration_rows, feature_names))
    calibration_labels = np.asarray([
        int(row.get("study_label") or 0) for row in calibration_rows
    ], dtype=np.int32)
    bins = quantile_calibration(calibration_scores, calibration_labels)
    test_scores = model.predict(build_matrix(test_rows, feature_names))
    calibrated = apply_calibration(test_scores, bins)
    scored = [
        {**row, "raw_score": float(score), "calibrated_probability": float(probability)}
        for row, score, probability in zip(test_rows, test_scores, calibrated)
    ]
    return {
        "name": experiment["name"], "model_path": experiment["model_path"],
        "feature_count": len(feature_names), "calibration_bins": bins,
        "natural_test_rows": len(test_rows),
        "natural_exceptional_winner_base_rate": round(float(np.mean([
            int(row.get("study_label") or 0) for row in test_rows
        ])), 6),
        "test_slices": evaluate_slices(scored, round_trip_cost_pct),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rows", type=Path, required=True)
    parser.add_argument("--premarket-features", type=Path, required=True)
    parser.add_argument("--premarket-labels", type=Path, required=True)
    parser.add_argument("--ablation-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--embargo-calendar-days", type=int, default=12)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()

    report = json.loads(args.ablation_report.read_text(encoding="utf-8"))
    labeled, label_coverage = join_open_entry_labels(
        read_jsonl(args.base_rows), read_jsonl(args.premarket_labels),
    )
    rows, feature_coverage = join_feature_rows(labeled, read_jsonl(args.premarket_features))
    calibration_rows, test_rows = chronological_partitions(
        rows, int(report["split"]["train_cutoff_datetime_ms"]),
        int(report["split"]["validation_cutoff_datetime_ms"]), args.embargo_calendar_days,
    )
    if not calibration_rows or not test_rows:
        raise ValueError("natural-universe calibration and test rows are required")
    evaluations = [
        evaluate_model(
            experiment, rows, calibration_rows, test_rows, args.round_trip_cost_pct,
        )
        for experiment in report["experiments"]
    ]
    output = {
        "status": "complete", "research_only": True, "execution_enabled": False,
        "warning": "Cohort drawdown is an approximation; prospective shadow validation remains required.",
        "round_trip_cost_pct": args.round_trip_cost_pct,
        "label_coverage": label_coverage, "feature_coverage": feature_coverage,
        "calibration_rows": len(calibration_rows), "test_rows": len(test_rows),
        "evaluations": evaluations, "promotion_gate": natural_promotion_gate(evaluations),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
