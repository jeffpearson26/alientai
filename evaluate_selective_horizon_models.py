from __future__ import annotations

"""One-time fixed-slice evaluation of all four selective horizon model heads."""

import argparse
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np

from audit_selective_challenger_validation import binary_auc, ranked_slices
from train_selective_five_day_challenger import (
    chronological_split,
    materialize_panel,
    matrix,
    premarket_for_labeled_rows,
    read_jsonl,
)
from alientai_v2.research.selective_premarket_features import join_natural_premarket_features


MODEL_FILES = {
    "positive_classifier": "positive_classifier.txt",
    "large_move_classifier": "large_move_classifier.txt",
    "expected_return_regressor": "expected_net_return_regressor.txt",
    "lower_quantile_regressor": "lower_quantile_net_return_regressor.txt",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon-sessions", type=int, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--premarket-features", type=Path)
    parser.add_argument(
        "--input-panel",
        type=Path,
        default=Path(r"D:\AlientAI\Data\FINRA_Short_Interest\features\natural_options_finra_research_panel_2026.jsonl"),
    )
    parser.add_argument("--daily-dir", type=Path, default=Path("data_v2/sp500_daily_schwab_max_history"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent

    rows, coverage = materialize_panel(
        read_jsonl(args.input_panel),
        root / args.daily_dir,
        args.horizon_sessions,
    )
    if args.premarket_features:
        eligible, excluded = premarket_for_labeled_rows(rows, read_jsonl(root / args.premarket_features))
        rows = join_natural_premarket_features(rows, eligible)
        coverage["premarket_rows_excluded_without_local_label"] = excluded

    models = {
        name: lgb.Booster(model_file=str(root / args.model_dir / filename))
        for name, filename in MODEL_FILES.items()
    }
    names = models["positive_classifier"].feature_name()
    x = matrix(rows, names)
    positive = np.asarray([int(row["label_positive_net_return"]) for row in rows], dtype=np.int32)
    large = np.asarray([int(row["label_large_move"]) for row in rows], dtype=np.int32)
    net = np.asarray([float(row["net_return_pct"]) for row in rows], dtype=np.float32)
    _, validation_idx, test_idx, split = chronological_split(rows)

    report: dict[str, Any] = {
        "build": f"ALIENTAI_SELECTIVE_{args.horizon_sessions}_DAY_ALL_MODEL_EVALUATION_V1",
        "research_only": True,
        "execution_enabled": False,
        "fixed_rank_fractions": [0.10, 0.05, 0.01],
        "coverage": coverage,
        "split": split,
        "models": {},
    }
    for name, model in models.items():
        validation_scores = model.predict(x[validation_idx])
        test_scores = model.predict(x[test_idx])
        target = large if name == "large_move_classifier" else positive
        result = {
            "validation_ranked_slices": ranked_slices(
                validation_scores, target[validation_idx], net[validation_idx]
            ),
            "untouched_test_ranked_slices": ranked_slices(
                test_scores, target[test_idx], net[test_idx]
            ),
        }
        if name.endswith("classifier"):
            result["validation_auc"] = binary_auc(target[validation_idx], validation_scores)
            result["untouched_test_auc"] = binary_auc(target[test_idx], test_scores)
        else:
            result["validation_return_correlation"] = float(
                np.corrcoef(validation_scores, net[validation_idx])[0, 1]
            )
            result["untouched_test_return_correlation"] = float(
                np.corrcoef(test_scores, net[test_idx])[0, 1]
            )
        report["models"][name] = result

    output = root / args.model_dir / "all_model_fixed_slice_evaluation.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
