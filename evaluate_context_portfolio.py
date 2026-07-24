from __future__ import annotations

"""Time-ordered, capacity-limited diagnostic for contextual unusual-call ideas.

This evaluator is deliberately research-only.  It selects a technical cutoff
from an earlier calibration period, leaves a calendar embargo, and evaluates
only later rows.  It does not make an already-explored data period prospective.
"""

import argparse
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.research.rare_signal_gate import evaluate_rare_signal_gate
from evaluate_matched_winner_full_universe import selection_metrics
from evaluate_unusual_call_contexts import score_rows
from evaluate_unusual_call_outcomes import join_option_outcomes, read_jsonl


def file_sha256(path: Path) -> str:
    """Return a stable artifact identity so a report can be reproduced later."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def split_chronologically(rows: Sequence[Mapping[str, Any]], calibration_fraction: float, embargo_calendar_days: int) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if not 0 < calibration_fraction < 1:
        raise ValueError("calibration_fraction must be in (0, 1)")
    days = sorted({date.fromisoformat(str(row["market_date"])) for row in rows})
    if len(days) < 3:
        raise ValueError("at least three distinct market dates are required")
    cutoff = days[max(0, min(len(days) - 2, int(len(days) * calibration_fraction) - 1))]
    test_start = cutoff + timedelta(days=embargo_calendar_days + 1)
    calibration = [row for row in rows if date.fromisoformat(str(row["market_date"])) <= cutoff]
    test = [row for row in rows if date.fromisoformat(str(row["market_date"])) >= test_start]
    if not calibration or not test:
        raise ValueError("chronological split produced an empty calibration or test slice")
    return calibration, test


def capacity_limited(rows: Sequence[Mapping[str, Any]], max_open_positions: int) -> list[Mapping[str, Any]]:
    if max_open_positions < 1:
        raise ValueError("max_open_positions must be positive")
    active_exits: list[date] = []
    selected = []
    for row in sorted(rows, key=lambda item: (str(item["market_date"]), -float(item["technical_context_score"]))):
        day = date.fromisoformat(str(row["market_date"]))
        # Free capital only after the exit-session close, a conservative rule.
        active_exits = [exit_day for exit_day in active_exits if day <= exit_day]
        if len(active_exits) >= max_open_positions:
            continue
        future = str(row.get("future_market_date") or "")
        try:
            exit_day = date.fromisoformat(future)
        except ValueError:
            continue
        if exit_day <= day:
            continue
        selected.append(row)
        active_exits.append(exit_day)
    return selected


def evaluate_cutoffs(calibration_rows: Sequence[Mapping[str, Any]], test_rows: Sequence[Mapping[str, Any]], fractions: Sequence[float], max_open_positions: int, round_trip_cost_pct: float) -> list[dict[str, Any]]:
    calibration_scores = np.asarray([float(row["technical_context_score"]) for row in calibration_rows], dtype=float)
    output = []
    for fraction in fractions:
        if not 0 < fraction <= 1:
            raise ValueError("fractions must be in (0, 1]")
        cutoff = float(np.quantile(calibration_scores, 1.0 - fraction))
        candidates = [row for row in test_rows if row.get("call_volume_unusual") and float(row["technical_context_score"]) >= cutoff]
        selected = capacity_limited(candidates, max_open_positions)
        metrics = selection_metrics(selected, round_trip_cost_pct)
        output.append({
            "technical_top_fraction_selected_on_calibration": fraction,
            "technical_score_cutoff_from_calibration": cutoff,
            "test_unusual_call_candidates": len(candidates),
            "max_open_positions": max_open_positions,
            **metrics,
            "rare_signal_gate": evaluate_rare_signal_gate(metrics),
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Chronological contextual unusual-call portfolio diagnostic.")
    parser.add_argument("--base-rows", type=Path, required=True)
    parser.add_argument("--option-features", type=Path, required=True)
    parser.add_argument("--technical-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--calibration-fraction", type=float, default=0.60)
    parser.add_argument("--embargo-calendar-days", type=int, default=7)
    parser.add_argument("--max-open-positions", type=int, default=5)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()
    raw_rows = join_option_outcomes(read_jsonl(args.base_rows), read_jsonl(args.option_features))
    model = lgb.Booster(model_file=str(args.technical_model))
    rows = score_rows(raw_rows, model)
    calibration, test = split_chronologically(rows, args.calibration_fraction, args.embargo_calendar_days)
    report = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "warning": "Retrospective chronological diagnostic only. Because this panel was previously explored, an independent future or untouched archive is still required for confirmation.",
        "calibration_rows": len(calibration),
        "test_rows": len(test),
        "calibration_fraction": args.calibration_fraction,
        "embargo_calendar_days": args.embargo_calendar_days,
        "round_trip_cost_pct": args.round_trip_cost_pct,
        "input_artifacts": {
            "base_rows_path": str(args.base_rows),
            "base_rows_sha256": file_sha256(args.base_rows),
            "option_features_path": str(args.option_features),
            "option_features_sha256": file_sha256(args.option_features),
            "technical_model_path": str(args.technical_model),
            "technical_model_sha256": file_sha256(args.technical_model),
        },
        "results": evaluate_cutoffs(calibration, test, (0.25, 0.10, 0.05), args.max_open_positions, args.round_trip_cost_pct),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
