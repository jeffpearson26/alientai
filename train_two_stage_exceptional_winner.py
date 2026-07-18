from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import lightgbm as lgb
import numpy as np

from alientai_v2.features.insider_purchase_features import safe_float
from evaluate_matched_winner_full_universe import build_matrix, non_overlapping, read_jsonl, selection_metrics


def date_from_ms(value: int) -> date:
    return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc).date()


def split_rows(
    rows: Sequence[Mapping[str, Any]], train_cutoff_ms: int, validation_cutoff_ms: int,
    embargo_calendar_days: int,
) -> Tuple[List[Mapping[str, Any]], List[Mapping[str, Any]], List[Mapping[str, Any]]]:
    train_cutoff = date_from_ms(train_cutoff_ms)
    validation_cutoff = date_from_ms(validation_cutoff_ms)
    train_end = train_cutoff - timedelta(days=embargo_calendar_days)
    validation_start = train_cutoff + timedelta(days=embargo_calendar_days)
    validation_end = validation_cutoff - timedelta(days=embargo_calendar_days)
    test_start = validation_cutoff + timedelta(days=embargo_calendar_days)
    train: List[Mapping[str, Any]] = []
    validation: List[Mapping[str, Any]] = []
    test: List[Mapping[str, Any]] = []
    for row in rows:
        day = date.fromisoformat(str(row["market_date"]))
        if day <= train_end:
            train.append(row)
        elif validation_start <= day <= validation_end:
            validation.append(row)
        elif day >= test_start:
            test.append(row)
    return train, validation, test


def targets(rows: Sequence[Mapping[str, Any]], cost_pct: float) -> Tuple[np.ndarray, np.ndarray]:
    net = np.asarray([safe_float(row["label_forward_return_5d_pct"]) - cost_pct for row in rows], dtype=np.float32)
    positive = (net > 0.0).astype(np.int32)
    clipped_return = np.clip(net, -20.0, 20.0)
    return positive, clipped_return


def train_models(
    x_train: np.ndarray, train_positive: np.ndarray, train_return: np.ndarray,
    x_validation: np.ndarray, validation_positive: np.ndarray, validation_return: np.ndarray,
    names: Sequence[str], rounds: int, early_stopping_rounds: int,
) -> Tuple[lgb.Booster, lgb.Booster]:
    common = {
        "learning_rate": 0.025, "num_leaves": 31, "min_data_in_leaf": 100,
        "feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 5,
        "lambda_l1": 2.0, "lambda_l2": 8.0, "verbosity": -1,
        "force_col_wise": True, "seed": 43, "num_threads": 0,
    }
    callbacks = [lgb.early_stopping(max(1, early_stopping_rounds)), lgb.log_evaluation(100)]
    classifier_train = lgb.Dataset(x_train, label=train_positive, feature_name=list(names))
    classifier_validation = lgb.Dataset(
        x_validation, label=validation_positive, reference=classifier_train, feature_name=list(names)
    )
    classifier = lgb.train(
        {**common, "objective": "binary", "metric": ["binary_logloss", "auc"]},
        classifier_train, num_boost_round=rounds,
        valid_sets=[classifier_validation], valid_names=["validation"], callbacks=callbacks,
    )
    regressor_train = lgb.Dataset(x_train, label=train_return, feature_name=list(names))
    regressor_validation = lgb.Dataset(
        x_validation, label=validation_return, reference=regressor_train, feature_name=list(names)
    )
    regressor = lgb.train(
        {**common, "objective": "huber", "metric": ["l1", "l2"]},
        regressor_train, num_boost_round=rounds,
        valid_sets=[regressor_validation], valid_names=["validation"], callbacks=callbacks,
    )
    return classifier, regressor


def attach_scores(
    rows: Sequence[Mapping[str, Any]], x: np.ndarray, discovery: lgb.Booster,
    positive: lgb.Booster, returns: lgb.Booster,
) -> List[Dict[str, Any]]:
    discovery_scores = discovery.predict(x, num_iteration=discovery.best_iteration)
    positive_scores = positive.predict(x, num_iteration=positive.best_iteration)
    return_scores = returns.predict(x, num_iteration=returns.best_iteration)
    return [
        {
            **row,
            "raw_score": float(discovery_score),
            "positive_net_probability": float(positive_score),
            "expected_net_return_pct": float(return_score),
        }
        for row, discovery_score, positive_score, return_score in zip(
            rows, discovery_scores, positive_scores, return_scores
        )
    ]


def apply_gate(rows: Sequence[Mapping[str, Any]], gate: Mapping[str, float]) -> List[Mapping[str, Any]]:
    return non_overlapping([
        row for row in rows
        if float(row["raw_score"]) >= gate["discovery_threshold"]
        and float(row["positive_net_probability"]) >= gate["positive_threshold"]
        and float(row["expected_net_return_pct"]) >= gate["expected_return_threshold"]
    ])


def choose_gate(
    validation_rows: Sequence[Mapping[str, Any]], cost_pct: float, minimum_signals: int = 100,
) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
    candidates: List[Dict[str, Any]] = []
    for discovery_threshold in (0.65, 0.70, 0.75, 0.80):
        for positive_threshold in (0.50, 0.525, 0.55, 0.575):
            for expected_return_threshold in (0.0, 0.25, 0.50, 0.75):
                gate = {
                    "discovery_threshold": discovery_threshold,
                    "positive_threshold": positive_threshold,
                    "expected_return_threshold": expected_return_threshold,
                }
                metrics = selection_metrics(apply_gate(validation_rows, gate), cost_pct)
                candidates.append({**gate, **metrics})
    eligible = [row for row in candidates if row.get("signals", 0) >= minimum_signals]
    if not eligible:
        raise ValueError("no validation gate meets the minimum signal requirement")
    profitable = [
        row for row in eligible
        if row.get("mean_net_return_pct", 0.0) > 0.0 and row.get("median_net_return_pct", 0.0) > 0.0
    ]
    pool = profitable or [row for row in eligible if row.get("mean_net_return_pct", 0.0) > 0.0] or eligible
    best = max(
        pool,
        key=lambda row: (
            row.get("exceptional_winner_rate", 0.0),
            row.get("mean_net_return_pct", -999.0),
            row.get("win_rate_after_cost", 0.0),
        ),
    )
    gate = {key: float(best[key]) for key in (
        "discovery_threshold", "positive_threshold", "expected_return_threshold"
    )}
    return gate, sorted(candidates, key=lambda row: row.get("exceptional_winner_rate", 0.0), reverse=True)


def importance(model: lgb.Booster) -> List[Dict[str, Any]]:
    return sorted(
        [
            {"feature": name, "gain": float(gain)}
            for name, gain in zip(model.feature_name(), model.feature_importance(importance_type="gain"))
        ],
        key=lambda row: row["gain"], reverse=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate a two-stage exceptional-winner research model.")
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--discovery-model", type=Path, required=True)
    parser.add_argument("--discovery-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--embargo-calendar-days", type=int, default=12)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    parser.add_argument("--minimum-validation-signals", type=int, default=100)
    parser.add_argument("--num-boost-round", type=int, default=1000)
    parser.add_argument("--early-stopping-rounds", type=int, default=75)
    args = parser.parse_args()

    rows = read_jsonl(args.rows)
    discovery_report = json.loads(args.discovery_report.read_text(encoding="utf-8"))
    discovery = lgb.Booster(model_file=str(args.discovery_model))
    names = discovery.feature_name()
    train_rows, validation_rows, test_rows = split_rows(
        rows,
        int(discovery_report["split"]["train_cutoff_datetime_ms"]),
        int(discovery_report["split"]["validation_cutoff_datetime_ms"]),
        args.embargo_calendar_days,
    )
    if not train_rows or not validation_rows or not test_rows:
        raise ValueError("chronological train, validation, and unseen test rows are required")
    x_train = build_matrix(train_rows, names)
    x_validation = build_matrix(validation_rows, names)
    x_test = build_matrix(test_rows, names)
    y_train_positive, y_train_return = targets(train_rows, args.round_trip_cost_pct)
    y_validation_positive, y_validation_return = targets(validation_rows, args.round_trip_cost_pct)
    positive, returns = train_models(
        x_train, y_train_positive, y_train_return,
        x_validation, y_validation_positive, y_validation_return,
        names, args.num_boost_round, args.early_stopping_rounds,
    )
    scored_validation = attach_scores(validation_rows, x_validation, discovery, positive, returns)
    gate, candidate_metrics = choose_gate(
        scored_validation, args.round_trip_cost_pct, args.minimum_validation_signals
    )
    validation_selected = apply_gate(scored_validation, gate)
    scored_test = attach_scores(test_rows, x_test, discovery, positive, returns)
    test_selected = apply_gate(scored_test, gate)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    positive_path = args.output_dir / "positive_net_classifier.txt"
    returns_path = args.output_dir / "expected_net_return_regressor.txt"
    positive.save_model(str(positive_path), num_iteration=positive.best_iteration)
    returns.save_model(str(returns_path), num_iteration=returns.best_iteration)
    report = {
        "status": "complete", "research_only": True, "execution_enabled": False,
        "warning": "The gate was selected on validation data. Only unseen test metrics estimate generalization.",
        "rows": {"train": len(train_rows), "validation": len(validation_rows), "test": len(test_rows)},
        "round_trip_cost_pct": args.round_trip_cost_pct,
        "selected_gate": gate,
        "validation_metrics": selection_metrics(validation_selected, args.round_trip_cost_pct),
        "unseen_test_metrics": selection_metrics(test_selected, args.round_trip_cost_pct),
        "validation_candidate_count": len(candidate_metrics),
        "top_validation_candidates": candidate_metrics[:10],
        "positive_model_best_iteration": int(positive.best_iteration),
        "return_model_best_iteration": int(returns.best_iteration),
        "positive_model_top_features": importance(positive)[:20],
        "return_model_top_features": importance(returns)[:20],
        "positive_model_path": str(positive_path),
        "return_model_path": str(returns_path),
    }
    report_path = args.output_dir / "two_stage_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
