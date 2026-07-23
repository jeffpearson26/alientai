from __future__ import annotations

"""Explore unusual call activity only within independently scored technical contexts.

This is an exploratory diagnostic, not a threshold-selection or trading tool.
The technical model must not include option features, preventing the context
score from directly reusing the call activity being tested.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.research.rare_signal_gate import evaluate_rare_signal_gate
from evaluate_matched_winner_full_universe import build_matrix, selection_metrics
from evaluate_unusual_call_outcomes import join_option_outcomes, read_jsonl


def score_rows(rows: Sequence[Mapping[str, Any]], model: lgb.Booster) -> list[dict[str, Any]]:
    scores = model.predict(build_matrix(rows, model.feature_name()))
    return [{**row, "technical_context_score": float(score)} for row, score in zip(rows, scores)]


def context_slices(rows: Sequence[Mapping[str, Any]], fractions: Sequence[float] = (0.25, 0.10, 0.05)) -> list[dict[str, Any]]:
    if not rows:
        return []
    scores = np.asarray([float(row["technical_context_score"]) for row in rows], dtype=float)
    output = []
    for fraction in fractions:
        if not 0 < fraction <= 1:
            raise ValueError("context fractions must be in (0, 1]")
        cutoff = float(np.quantile(scores, 1.0 - fraction))
        selected = [row for row in rows if row.get("call_volume_unusual") and float(row["technical_context_score"]) >= cutoff]
        output.append({"technical_top_fraction": fraction, "technical_score_cutoff": cutoff, "rows": selected})
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore unusual calls within a technical-only context.")
    parser.add_argument("--base-rows", type=Path, required=True)
    parser.add_argument("--option-features", type=Path, required=True)
    parser.add_argument("--technical-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()
    rows = join_option_outcomes(read_jsonl(args.base_rows), read_jsonl(args.option_features))
    model = lgb.Booster(model_file=str(args.technical_model))
    scored = score_rows(rows, model)
    slices = []
    for item in context_slices(scored):
        metrics = selection_metrics(item.pop("rows"), args.round_trip_cost_pct)
        slices.append({**item, **metrics, "rare_signal_gate": evaluate_rare_signal_gate(metrics)})
    report = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "warning": "Exploratory contextual analysis only. Score bands must be independently revalidated before any threshold is retained.",
        "rows": len(scored),
        "round_trip_cost_pct": args.round_trip_cost_pct,
        "unusual_calls_with_technical_context": slices,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
