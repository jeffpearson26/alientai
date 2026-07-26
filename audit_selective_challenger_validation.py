"""Validation-only diagnostic for the frozen selective five-day challenger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import lightgbm as lgb
import numpy as np

from train_selective_five_day_challenger import (
    chronological_split,
    materialize_panel,
    matrix,
    read_jsonl,
)


BUILD = "ALIENTAI_SELECTIVE_CHALLENGER_VALIDATION_AUDIT_V1"


def binary_auc(labels: np.ndarray, scores: np.ndarray) -> float | None:
    labels = np.asarray(labels, dtype=np.int32)
    scores = np.asarray(scores, dtype=float)
    positive = int(np.sum(labels == 1))
    negative = int(np.sum(labels == 0))
    if positive == 0 or negative == 0:
        return None
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=float)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and scores[order[end]] == scores[order[start]]:
            end += 1
        ranks[order[start:end]] = ((start + 1) + end) / 2.0
        start = end
    rank_sum = float(np.sum(ranks[labels == 1]))
    return (rank_sum - positive * (positive + 1) / 2.0) / (positive * negative)


def ranked_slices(
    scores: np.ndarray,
    labels: np.ndarray,
    returns: np.ndarray,
    fractions: Sequence[float] = (0.10, 0.05, 0.01),
) -> list[dict[str, Any]]:
    order = np.argsort(scores)[::-1]
    result = []
    for fraction in fractions:
        count = max(1, int(len(order) * fraction))
        selected = order[:count]
        result.append({
            "top_fraction": fraction,
            "rows": int(count),
            "positive_rate": float(np.mean(labels[selected])),
            "mean_net_return_pct": float(np.mean(returns[selected])),
            "median_net_return_pct": float(np.median(returns[selected])),
            "win_rate_after_cost": float(np.mean(returns[selected] > 0.0)),
        })
    return result


def importance(model: lgb.Booster, limit: int = 20) -> list[dict[str, Any]]:
    rows = [
        {"feature": name, "gain": float(gain)}
        for name, gain in zip(
            model.feature_name(),
            model.feature_importance(importance_type="gain"),
        )
    ]
    return sorted(rows, key=lambda row: row["gain"], reverse=True)[:limit]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-panel",
        default=r"D:\AlientAI\Data\FINRA_Short_Interest\features\natural_options_finra_research_panel_2026.jsonl",
    )
    parser.add_argument("--daily-dir", default="data_v2/sp500_daily_schwab_max_history")
    parser.add_argument("--model-dir", default="data_v2/selective_five_day_challenger_training")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    rows, coverage = materialize_panel(
        read_jsonl(Path(args.input_panel)),
        (root / args.daily_dir).resolve(),
    )
    model_dir = (root / args.model_dir).resolve()
    positive_model = lgb.Booster(model_file=str(model_dir / "positive_classifier.txt"))
    large_model = lgb.Booster(model_file=str(model_dir / "large_move_classifier.txt"))
    expected_model = lgb.Booster(model_file=str(model_dir / "expected_net_return_regressor.txt"))
    lower_model = lgb.Booster(model_file=str(model_dir / "lower_quantile_net_return_regressor.txt"))
    names = positive_model.feature_name()
    x = matrix(rows, names)
    positive = np.asarray([int(row["label_positive_net_return"]) for row in rows], dtype=np.int32)
    large = np.asarray([int(row["label_large_move"]) for row in rows], dtype=np.int32)
    net = np.asarray([float(row["net_return_pct"]) for row in rows], dtype=np.float32)
    _, validation_idx, _, split = chronological_split(rows)

    positive_scores = positive_model.predict(x[validation_idx])
    large_scores = large_model.predict(x[validation_idx])
    expected = expected_model.predict(x[validation_idx])
    lower = lower_model.predict(x[validation_idx])
    expected_correlation = float(np.corrcoef(expected, net[validation_idx])[0, 1])
    lower_correlation = float(np.corrcoef(lower, net[validation_idx])[0, 1])
    report = {
        "build": BUILD,
        "status": "VALIDATION_DIAGNOSTIC_ONLY",
        "research_only": True,
        "execution_enabled": False,
        "test_partition_inspected": False,
        "coverage": coverage,
        "split": split,
        "validation_rows": int(len(validation_idx)),
        "positive_classifier": {
            "auc": binary_auc(positive[validation_idx], positive_scores),
            "brier_score": float(np.mean((positive_scores - positive[validation_idx]) ** 2)),
            "base_rate": float(np.mean(positive[validation_idx])),
            "ranked_slices": ranked_slices(
                positive_scores, positive[validation_idx], net[validation_idx],
            ),
            "top_features": importance(positive_model),
        },
        "large_move_classifier": {
            "auc": binary_auc(large[validation_idx], large_scores),
            "brier_score": float(np.mean((large_scores - large[validation_idx]) ** 2)),
            "base_rate": float(np.mean(large[validation_idx])),
            "ranked_slices": ranked_slices(
                large_scores, large[validation_idx], net[validation_idx],
            ),
            "top_features": importance(large_model),
        },
        "expected_return_regressor": {
            "pearson_correlation": expected_correlation,
            "mae_pct": float(np.mean(np.abs(expected - net[validation_idx]))),
            "top_features": importance(expected_model),
        },
        "lower_quantile_regressor": {
            "pearson_correlation": lower_correlation,
            "top_features": importance(lower_model),
        },
        "next_action_rule": (
            "Use this validation audit only to decide whether a materially new, "
            "preregistered future-period challenger is justified. Never retune "
            "or rescore the already observed test partition."
        ),
    }
    output = model_dir / "validation_component_audit.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
