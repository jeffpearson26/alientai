from __future__ import annotations

"""Pre-specify a technical-score cutoff, then evaluate only a later holdout."""

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.research.rare_signal_gate import evaluate_rare_signal_gate
from evaluate_matched_winner_full_universe import selection_metrics
from evaluate_unusual_call_outcomes import join_option_outcomes, read_jsonl
from score_natural_technical_context import score_rows


def partition(rows: Sequence[Mapping[str, Any]], calibration_end: str, holdout_start: str) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    calibration_end_day = date.fromisoformat(calibration_end)
    holdout_start_day = date.fromisoformat(holdout_start)
    if holdout_start_day <= calibration_end_day:
        raise ValueError("holdout start must be later than calibration end")
    calibration, holdout = [], []
    for row in rows:
        day = date.fromisoformat(str(row["market_date"]))
        if day <= calibration_end_day:
            calibration.append(row)
        elif day >= holdout_start_day:
            holdout.append(row)
    if not calibration or not holdout:
        raise ValueError("both calibration and holdout rows are required")
    return calibration, holdout


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate one pre-specified unusual-call context on later holdout rows.")
    parser.add_argument("--base-rows", type=Path, required=True)
    parser.add_argument("--call-history", type=Path, required=True)
    parser.add_argument("--technical-model", type=Path, required=True)
    parser.add_argument("--calibration-end", required=True)
    parser.add_argument("--holdout-start", required=True)
    parser.add_argument("--technical-top-fraction", type=float, default=0.05)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()
    if not 0 < args.technical_top_fraction < 1:
        raise ValueError("technical top fraction must be in (0, 1)")
    rows = join_option_outcomes(read_jsonl(args.base_rows), read_jsonl(args.call_history))
    model = lgb.Booster(model_file=str(args.technical_model))
    scored = score_rows(rows, model.feature_name(), model)
    calibration, holdout = partition(scored, args.calibration_end, args.holdout_start)
    cutoff = float(np.quantile([row["technical_context_score"] for row in calibration], 1.0 - args.technical_top_fraction))
    selected = [row for row in holdout if row.get("call_volume_unusual") and row["technical_context_score"] >= cutoff]
    report = {
        "status": "complete", "research_only": True, "execution_enabled": False,
        "warning": "One pre-specified research rule evaluated only on later holdout dates; not a trading recommendation.",
        "rule": {"technical_top_fraction_calibration": args.technical_top_fraction, "technical_score_cutoff": cutoff,
                 "requires_unusual_call_volume": True},
        "calibration_rows": len(calibration), "holdout_rows": len(holdout),
        "calibration_end": args.calibration_end, "holdout_start": args.holdout_start,
        "round_trip_cost_pct": args.round_trip_cost_pct,
        "holdout_metrics": selection_metrics(selected, args.round_trip_cost_pct),
    }
    report["rare_signal_gate"] = evaluate_rare_signal_gate(report["holdout_metrics"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
