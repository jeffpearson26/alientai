from __future__ import annotations

"""Fit validation-only Nasdaq score calibration and audit later reliability."""

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Sequence

import lightgbm as lgb

from alientai_v2.research.score_calibration import (
    brier_score,
    calibrated_probability,
    expected_calibration_error,
    fit_isotonic,
    percentile_rank,
)
from evaluate_context_portfolio import file_sha256
from evaluate_nasdaq100_clone_portfolio import read_jsonl, score_rows


def reliability(
    scores: Sequence[float],
    labels: Sequence[int],
    blocks: Sequence[dict[str, float]],
) -> dict[str, Any]:
    probabilities = [calibrated_probability(score, blocks) for score in scores]
    prevalence = sum(labels) / len(labels)
    return {
        "rows": len(labels),
        "base_rate": round(prevalence, 6),
        "raw_score_brier": round(brier_score(scores, labels), 6),
        "calibrated_brier": round(brier_score(probabilities, labels), 6),
        "base_rate_brier": round(brier_score([prevalence] * len(labels), labels), 6),
        "calibrated_ece_10_bins": round(
            expected_calibration_error(probabilities, labels, 10), 6
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--training-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--winner-return-pct", type=float, default=10.0)
    parser.add_argument("--selected-score-cutoff", type=float, required=True)
    args = parser.parse_args()

    training = json.loads(args.training_report.read_text(encoding="utf-8"))
    rows = read_jsonl(args.rows)
    model = lgb.Booster(model_file=str(args.model))
    scored = score_rows(rows, model, training["feature_names"])
    validation_start = date.fromisoformat(training["split"]["validation_start"])
    validation_end = date.fromisoformat(training["split"]["validation_end"])
    confirmation_start = date.fromisoformat(training["split"]["test_start"])
    validation = [
        row for row in scored
        if validation_start <= date.fromisoformat(row["market_date"]) <= validation_end
    ]
    confirmation = [
        row for row in scored
        if date.fromisoformat(row["market_date"]) >= confirmation_start
    ]
    validation_scores = [float(row["technical_context_score"]) for row in validation]
    validation_labels = [
        int(float(row["label_forward_return_5d_pct"]) >= args.winner_return_pct)
        for row in validation
    ]
    blocks = fit_isotonic(validation_scores, validation_labels)
    confirmation_scores = [
        float(row["technical_context_score"]) for row in confirmation
    ]
    confirmation_labels = [
        int(float(row["label_forward_return_5d_pct"]) >= args.winner_return_pct)
        for row in confirmation
    ]
    cutoff_probability = calibrated_probability(args.selected_score_cutoff, blocks)
    cutoff_rank = percentile_rank(args.selected_score_cutoff, validation_scores)
    report = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "warning": "Calibrated probability estimates a >=10% five-day historical outcome, not the probability of profit. Confirmation is reused historical evidence; prospective calibration is still required.",
        "definitions": {
            "confidence_rank_1_to_100": "validation empirical score percentile; relative rank, not probability",
            "calibrated_exceptional_move_probability": f"isotonic estimate of gross five-day return >= {args.winner_return_pct}%",
        },
        "artifacts": {
            "rows_sha256": file_sha256(args.rows),
            "model_sha256": file_sha256(args.model),
            "training_report_sha256": file_sha256(args.training_report),
        },
        "winner_return_pct": args.winner_return_pct,
        "selected_score_cutoff": args.selected_score_cutoff,
        "selected_cutoff_confidence_rank_1_to_100": cutoff_rank,
        "selected_cutoff_calibrated_exceptional_move_probability": round(cutoff_probability, 6),
        "validation_score_reference": {
            "count": len(validation_scores),
            "sorted_scores": sorted(validation_scores),
        },
        "isotonic_blocks": blocks,
        "validation_in_sample_calibration": reliability(
            validation_scores, validation_labels, blocks
        ),
        "reused_historical_confirmation_calibration": reliability(
            confirmation_scores, confirmation_labels, blocks
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        key: value for key, value in report.items()
        if key not in {"validation_score_reference", "isotonic_blocks"}
    }, indent=2))


if __name__ == "__main__":
    main()
