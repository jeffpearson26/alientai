"""Freeze a five-day LightGBM threshold from validation, then report its test result.

This is deliberately a report auditor: it never loads a model, retrains, scores
symbols, writes to Supabase, or touches execution settings.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable


BUILD = "ALIENTAI_LIGHTGBM_5DAY_LOCKED_HOLDOUT_AUDIT_V1"


def _threshold_rows(partition: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    rows = partition.get("thresholds")
    if not isinstance(rows, list):
        raise ValueError("report partition has no threshold metrics")
    for row in rows:
        if not isinstance(row, dict) or "threshold" not in row:
            raise ValueError("report contains an invalid threshold metric")
        yield row


def select_validation_threshold(validation: Dict[str, Any], minimum_signals: int) -> Dict[str, Any]:
    """Select only from validation data, preferring net return then sample size."""
    eligible = [
        row for row in _threshold_rows(validation)
        if int(row.get("signal_count") or 0) >= minimum_signals
        and row.get("avg_net_return_pct") is not None
    ]
    if not eligible:
        raise ValueError("no validation threshold meets the minimum signal count")
    return max(
        eligible,
        key=lambda row: (
            float(row["avg_net_return_pct"]),
            int(row.get("non_overlapping_signal_count") or 0),
            int(row.get("signal_count") or 0),
            float(row["threshold"]),
        ),
    )


def matching_threshold(partition: Dict[str, Any], threshold: float) -> Dict[str, Any]:
    for row in _threshold_rows(partition):
        if float(row["threshold"]) == float(threshold):
            return row
    raise ValueError("test partition does not contain the validation-locked threshold")


def audit_report(report: Dict[str, Any], minimum_validation_signals: int) -> Dict[str, Any]:
    validation = report.get("validation_metrics")
    test = report.get("test_metrics")
    if not isinstance(validation, dict) or not isinstance(test, dict):
        raise ValueError("report requires validation_metrics and test_metrics")
    chosen = select_validation_threshold(validation, minimum_validation_signals)
    test_row = matching_threshold(test, float(chosen["threshold"]))
    return {
        "build": BUILD,
        "research_only": True,
        "execution_enabled": False,
        "selection_rule": "highest validation avg_net_return_pct among thresholds meeting the minimum validation signal count; test never participates in selection",
        "minimum_validation_signals": int(minimum_validation_signals),
        "target_return_pct": report.get("target_return_pct"),
        "round_trip_cost_pct": report.get("round_trip_cost_pct"),
        "locked_threshold": float(chosen["threshold"]),
        "validation": chosen,
        "untouched_test": test_row,
        "status": "RESEARCH_HOLD",
        "note": "This audit prevents test-threshold selection, but does not make an already-observed historical test period newly independent.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--minimum-validation-signals", type=int, default=30)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.minimum_validation_signals < 1:
        raise ValueError("minimum validation signals must be positive")
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    output = audit_report(report, args.minimum_validation_signals)
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
