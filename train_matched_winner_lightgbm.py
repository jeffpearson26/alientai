from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import lightgbm as lgb
import numpy as np

from alientai_v2.features.insider_purchase_features import safe_float
from alientai_v2.research.matched_winner_study import DEFAULT_ANALYSIS_FEATURES
from train_v2_transformer_20day_sp500_from_supabase import chronological_three_way_indices, now_iso


ROOT = Path(__file__).resolve().parent


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def eligible_features(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    features: List[str] = []
    for name in DEFAULT_ANALYSIS_FEATURES:
        if name.startswith("label_"):
            raise ValueError("future outcome labels cannot be model features")
        values = [safe_float(row.get(name)) for row in rows if row.get(name) is not None]
        if values and max(values) != min(values):
            features.append(name)
    return features


def prepare_matrix(
    rows: Sequence[Mapping[str, Any]], features: Sequence[str],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    names: List[str] = []
    columns: List[np.ndarray] = []
    for feature in features:
        if feature.startswith("label_"):
            raise ValueError("future outcome labels cannot be model features")
        missing = np.asarray([row.get(feature) is None for row in rows], dtype=np.float32)
        values = np.asarray([safe_float(row.get(feature)) for row in rows], dtype=np.float32)
        names.append(feature)
        columns.append(values)
        if np.any(missing):
            names.append(f"{feature}__missing")
            columns.append(missing)
    x = np.column_stack(columns).astype(np.float32) if columns else np.empty((len(rows), 0), dtype=np.float32)
    y = np.asarray([int(row.get("study_label") or 0) for row in rows], dtype=np.int32)
    timestamps = np.asarray([
        int(datetime.fromisoformat(str(row.get("market_date"))).replace(tzinfo=timezone.utc).timestamp() * 1000)
        for row in rows
    ], dtype=np.int64)
    return x, y, timestamps, names


def event_balancing_weights(rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    control_counts = Counter(
        str(row.get("study_event_id")) for row in rows if row.get("study_role") == "control"
    )
    weights = []
    for row in rows:
        if row.get("study_role") == "winner":
            weights.append(1.0)
        else:
            count = control_counts.get(str(row.get("study_event_id")), 1)
            weights.append(1.0 / max(1, count))
    return np.asarray(weights, dtype=np.float32)


def score_metrics(labels: np.ndarray, scores: np.ndarray) -> Dict[str, Any]:
    thresholds = []
    for threshold in (0.50, 0.60, 0.70, 0.80, 0.90):
        selected = scores >= threshold
        thresholds.append({
            "threshold": threshold,
            "selected_count": int(np.sum(selected)),
            "matched_set_precision": round(float(np.mean(labels[selected])), 6) if np.any(selected) else None,
        })
    order = np.argsort(-scores)
    top_fractions = []
    for fraction in (0.01, 0.05, 0.10):
        count = max(1, int(len(order) * fraction))
        chosen = order[:count]
        top_fractions.append({
            "fraction": fraction, "selected_count": count,
            "matched_set_precision": round(float(np.mean(labels[chosen])), 6),
            "lift_vs_matched_base": round(float(np.mean(labels[chosen]) / max(np.mean(labels), 1e-12)), 6),
        })
    return {
        "rows": int(labels.size),
        "matched_base_rate": round(float(np.mean(labels)), 6),
        "thresholds": thresholds,
        "top_score_fractions": top_fractions,
    }


def train_model(
    x: np.ndarray, y: np.ndarray, weights: np.ndarray,
    train_idx: np.ndarray, validation_idx: np.ndarray, names: Sequence[str],
    num_boost_round: int, early_stopping_rounds: int,
) -> lgb.Booster:
    train = lgb.Dataset(x[train_idx], label=y[train_idx], weight=weights[train_idx], feature_name=list(names))
    validation = lgb.Dataset(
        x[validation_idx], label=y[validation_idx], weight=weights[validation_idx],
        reference=train, feature_name=list(names),
    )
    return lgb.train(
        {
            "objective": "binary", "metric": ["binary_logloss", "auc"],
            "learning_rate": 0.025, "num_leaves": 31, "min_data_in_leaf": 50,
            "feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 5,
            "lambda_l1": 2.0, "lambda_l2": 6.0, "verbosity": -1,
            "force_col_wise": True, "seed": 42,
        },
        train, num_boost_round=max(1, num_boost_round),
        valid_sets=[validation], valid_names=["validation"],
        callbacks=[lgb.early_stopping(max(1, early_stopping_rounds)), lgb.log_evaluation(50)],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a matched exceptional-winner LightGBM discovery model.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--train-fraction", type=float, default=0.60)
    parser.add_argument("--validation-fraction", type=float, default=0.20)
    parser.add_argument("--embargo-calendar-days", type=int, default=12)
    parser.add_argument("--num-boost-round", type=int, default=1000)
    parser.add_argument("--early-stopping-rounds", type=int, default=75)
    args = parser.parse_args()

    rows = read_jsonl(args.input)
    features = eligible_features(rows)
    x, y, timestamps, names = prepare_matrix(rows, features)
    weights = event_balancing_weights(rows)
    train_idx, validation_idx, test_idx, split = chronological_three_way_indices(
        timestamps, train_fraction=args.train_fraction,
        validation_fraction=args.validation_fraction,
        embargo_calendar_days=args.embargo_calendar_days,
    )
    model = train_model(
        x, y, weights, train_idx, validation_idx, names,
        args.num_boost_round, args.early_stopping_rounds,
    )
    predict = lambda indices: model.predict(x[indices], num_iteration=model.best_iteration)
    importance = sorted(
        ({"feature": name, "gain": float(gain)} for name, gain in zip(names, model.feature_importance(importance_type="gain"))),
        key=lambda row: row["gain"], reverse=True,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "matched_winner_classifier.txt"
    model.save_model(str(model_path), num_iteration=model.best_iteration)
    report = {
        "status": "complete", "finished_at": now_iso(),
        "research_only": True, "execution_enabled": False,
        "score_is_real_world_probability": False,
        "warning": "Case-control sampling changes class prevalence; scores require calibration on the full universe.",
        "input": str(args.input), "rows": len(rows), "feature_count": len(names),
        "best_iteration": int(model.best_iteration), "split": split,
        "train_metrics": score_metrics(y[train_idx], predict(train_idx)),
        "validation_metrics": score_metrics(y[validation_idx], predict(validation_idx)),
        "test_metrics": score_metrics(y[test_idx], predict(test_idx)),
        "top_features": importance[:40], "model_path": str(model_path),
    }
    report_path = args.output_dir / "matched_winner_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
