from __future__ import annotations

"""Freeze a validation-only shadow policy for the two-day large-move lead."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np

from train_selective_five_day_challenger import (
    chronological_split,
    materialize_panel,
    matrix,
    premarket_for_labeled_rows,
    read_jsonl,
)
from alientai_v2.research.selective_premarket_features import join_natural_premarket_features


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_policy(validation_scores: np.ndarray, top_fraction: float = 0.01) -> dict[str, Any]:
    scores = np.asarray(validation_scores, dtype=float)
    if not len(scores):
        raise ValueError("validation scores are required")
    if not 0.0 < top_fraction < 1.0:
        raise ValueError("top_fraction must be between zero and one")
    return {
        "score_cutoff": float(np.quantile(scores, 1.0 - top_fraction, method="higher")),
        "validation_top_fraction": float(top_fraction),
        "minimum_universe_coverage_fraction": 0.95,
        "maximum_candidates": None,
        "decision": "SHADOW_OBSERVE_ONLY",
        "execution_enabled": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-panel",
        type=Path,
        default=Path(r"D:\AlientAI\Data\FINRA_Short_Interest\features\natural_options_finra_research_panel_2026.jsonl"),
    )
    parser.add_argument("--daily-dir", type=Path, default=Path("data_v2/sp500_daily_schwab_max_history"))
    parser.add_argument(
        "--premarket-features",
        type=Path,
        default=Path("data_v2/rcef_research/selective_natural_premarket_features_2026.jsonl"),
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("data_v2/selective_two_day_challenger_premarket_20260726"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data_v2/rcef_research/selective_two_day_shadow_policy.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent

    rows, coverage = materialize_panel(read_jsonl(args.input_panel), root / args.daily_dir, 2)
    eligible, excluded = premarket_for_labeled_rows(rows, read_jsonl(root / args.premarket_features))
    rows = join_natural_premarket_features(rows, eligible)
    _, validation_idx, _, split = chronological_split(rows)
    model_path = root / args.model_dir / "large_move_classifier.txt"
    model = lgb.Booster(model_file=str(model_path))
    scores = model.predict(matrix(rows, model.feature_name()))
    frozen = freeze_policy(scores[validation_idx])
    report = {
        "build": "ALIENTAI_SELECTIVE_TWO_DAY_SHADOW_POLICY_V1",
        "status": "FROZEN_FOR_FUTURE_SHADOW_ONLY",
        "research_only": True,
        "horizon_sessions": 2,
        "target": "net_return_at_least_2pct_after_0.25pct_round_trip_cost",
        "entry_assumption": "next_regular_session_open",
        "exit_assumption": "second_regular_session_close",
        "model_path": str(model_path.resolve()),
        "model_sha256": sha256(model_path),
        "feature_names": model.feature_name(),
        "coverage": {**coverage, "premarket_rows_excluded_without_local_label": excluded},
        "split": split,
        "policy": frozen,
        "prohibitions": [
            "no threshold retuning on the observed test partition",
            "no paper or live order creation",
            "no scoring an incomplete universe",
            "no substitution of matched winner/control premarket data",
        ],
    }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
