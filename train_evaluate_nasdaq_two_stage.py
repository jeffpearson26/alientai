from __future__ import annotations

"""Research-only classifier plus expected-return Nasdaq ranker."""

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from evaluate_context_portfolio import (
    capital_scaled_drawdown,
    capacity_limited,
    daily_archive_sha256,
    file_sha256,
    load_daily_closes,
)
from evaluate_nasdaq100_clone_portfolio import trade_metrics
from train_natural_technical_context import (
    chronological_split,
    matrix,
    read_jsonl,
    technical_feature_names,
)


METHODS = ("classifier", "expected_return", "joint")


def score_methods(
    classifier_scores: np.ndarray, expected_returns: np.ndarray,
) -> dict[str, np.ndarray]:
    if classifier_scores.shape != expected_returns.shape:
        raise ValueError("classifier and return predictions must have identical shape")
    return {
        "classifier": classifier_scores.astype(float),
        "expected_return": expected_returns.astype(float),
        "joint": classifier_scores.astype(float)
        * np.maximum(expected_returns.astype(float), 0.0),
    }


def validation_choice(
    rows: Sequence[Mapping[str, Any]],
    scores: Mapping[str, np.ndarray],
    fractions: Sequence[float],
    minimum_signals: int,
    cost_pct: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    diagnostics = []
    for method in METHODS:
        values = np.asarray(scores[method], dtype=float)
        for fraction in fractions:
            intended_signals = max(1, int(len(values) * fraction))
            cutoff = float(np.quantile(values, 1.0 - fraction))
            selected = [row for row, score in zip(rows, values) if score >= cutoff]
            metrics = trade_metrics(selected, cost_pct)
            diagnostics.append({
                "method": method,
                "fraction": float(fraction),
                "cutoff": cutoff,
                "intended_signals": intended_signals,
                "tie_expansion_ratio": round(len(selected) / intended_signals, 6),
                **metrics,
            })
    eligible = [
        row for row in diagnostics
        if row["signals"] >= minimum_signals
        and row["mean_net_return_pct"] is not None
        and row["mean_net_return_pct"] > 0.0
        and row["median_net_return_pct"] > 0.0
        and row["net_win_rate_pct"] >= 50.0
        and row["tie_expansion_ratio"] <= 1.5
    ]
    if not eligible:
        raise ValueError("no validation candidate meets minimum_signals")
    winner = max(
        eligible,
        key=lambda row: (
            row["mean_net_return_pct"],
            row["median_net_return_pct"],
            -row["fraction"],
        ),
    )
    return winner, diagnostics


def train_models(
    x: np.ndarray,
    gross_returns: np.ndarray,
    train_idx: np.ndarray,
    validation_idx: np.ndarray,
    feature_names: Sequence[str],
    winner_return_pct: float,
    rounds: int,
    early_stopping: int,
) -> tuple[lgb.Booster, lgb.Booster]:
    labels = (gross_returns >= winner_return_pct).astype(np.int32)
    train_classifier = lgb.Dataset(
        x[train_idx], label=labels[train_idx], feature_name=list(feature_names)
    )
    validation_classifier = lgb.Dataset(
        x[validation_idx],
        label=labels[validation_idx],
        reference=train_classifier,
        feature_name=list(feature_names),
    )
    common = {
        "learning_rate": 0.025,
        "num_leaves": 31,
        "min_data_in_leaf": 100,
        "feature_fraction": 0.85,
        "lambda_l1": 2.0,
        "lambda_l2": 8.0,
        "verbosity": -1,
        "seed": 42,
        "force_col_wise": True,
    }
    classifier = lgb.train(
        {**common, "objective": "binary", "metric": ["binary_logloss", "auc"]},
        train_classifier,
        num_boost_round=rounds,
        valid_sets=[validation_classifier],
        callbacks=[
            lgb.early_stopping(early_stopping, verbose=False),
            lgb.log_evaluation(0),
        ],
    )
    train_regressor = lgb.Dataset(
        x[train_idx], label=gross_returns[train_idx], feature_name=list(feature_names)
    )
    validation_regressor = lgb.Dataset(
        x[validation_idx],
        label=gross_returns[validation_idx],
        reference=train_regressor,
        feature_name=list(feature_names),
    )
    regressor = lgb.train(
        {**common, "objective": "regression_l1", "metric": "l1"},
        train_regressor,
        num_boost_round=rounds,
        valid_sets=[validation_regressor],
        callbacks=[
            lgb.early_stopping(early_stopping, verbose=False),
            lgb.log_evaluation(0),
        ],
    )
    return classifier, regressor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--winner-return-pct", type=float, default=10.0)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    parser.add_argument("--fractions", type=float, nargs="+", default=[0.0025, 0.005, 0.01])
    parser.add_argument("--minimum-validation-signals", type=int, default=20)
    parser.add_argument("--max-open-positions", type=int, default=5)
    parser.add_argument("--train-fraction", type=float, default=0.60)
    parser.add_argument("--validation-fraction", type=float, default=0.20)
    parser.add_argument("--embargo-calendar-days", type=int, default=12)
    parser.add_argument("--num-boost-round", type=int, default=800)
    parser.add_argument("--early-stopping-rounds", type=int, default=60)
    args = parser.parse_args()

    rows = [
        row for row in read_jsonl(args.rows)
        if row.get("label_forward_return_5d_pct") is not None and row.get("market_date")
    ]
    names = technical_feature_names(rows)
    x = matrix(rows, names)
    returns = np.asarray(
        [float(row["label_forward_return_5d_pct"]) for row in rows], dtype=np.float32
    )
    train_idx, validation_idx, test_idx, split = chronological_split(
        rows,
        args.train_fraction,
        args.validation_fraction,
        args.embargo_calendar_days,
    )
    classifier, regressor = train_models(
        x,
        returns,
        train_idx,
        validation_idx,
        names,
        args.winner_return_pct,
        args.num_boost_round,
        args.early_stopping_rounds,
    )
    predict = lambda model, indexes: model.predict(
        x[indexes], num_iteration=model.best_iteration
    )
    validation_scores = score_methods(
        predict(classifier, validation_idx), predict(regressor, validation_idx)
    )
    winner, diagnostics = validation_choice(
        [rows[index] for index in validation_idx],
        validation_scores,
        args.fractions,
        args.minimum_validation_signals,
        args.round_trip_cost_pct,
    )
    test_scores = score_methods(
        predict(classifier, test_idx), predict(regressor, test_idx)
    )[winner["method"]]
    test_rows = [rows[index] for index in test_idx]
    candidates = [
        {
            **row,
            "two_stage_score": float(score),
            # Reuse the established deterministic capacity allocator.
            "technical_context_score": float(score),
        }
        for row, score in zip(test_rows, test_scores)
        if float(score) >= winner["cutoff"]
    ]
    selected = capacity_limited(candidates, args.max_open_positions)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    classifier_path = args.output_dir / "classifier.txt"
    regressor_path = args.output_dir / "expected_return_regressor.txt"
    classifier.save_model(str(classifier_path), num_iteration=classifier.best_iteration)
    regressor.save_model(str(regressor_path), num_iteration=regressor.best_iteration)
    report = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "warning": "The historical confirmation period has been used by prior Nasdaq experiments; this is not a fresh untouched test.",
        "selection_contract": "method, fraction, and cutoff selected using validation only",
        "artifacts": {
            "rows_sha256": file_sha256(args.rows),
            "daily_archive_sha256": daily_archive_sha256(args.daily_dir),
        },
        "settings": {
            "winner_return_pct": args.winner_return_pct,
            "round_trip_cost_pct": args.round_trip_cost_pct,
            "candidate_methods": list(METHODS),
            "candidate_fractions": args.fractions,
            "minimum_validation_signals": args.minimum_validation_signals,
            "max_open_positions": args.max_open_positions,
        },
        "feature_names": names,
        "split": split,
        "classifier_best_iteration": int(classifier.best_iteration),
        "regressor_best_iteration": int(regressor.best_iteration),
        "validation_diagnostics": diagnostics,
        "selected": winner,
        "historical_confirmation_candidates_before_capacity": len(candidates),
        "historical_confirmation": {
            **trade_metrics(selected, args.round_trip_cost_pct),
            **capital_scaled_drawdown(
                selected,
                load_daily_closes(args.daily_dir),
                args.max_open_positions,
                args.round_trip_cost_pct,
            ),
        },
        "model_paths": {
            "classifier": str(classifier_path),
            "expected_return_regressor": str(regressor_path),
        },
    }
    report_path = args.output_dir / "two_stage_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
