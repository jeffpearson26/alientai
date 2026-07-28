from __future__ import annotations

"""Research-only Nasdaq models specialized by point-in-time QQQ regime."""

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


REGIMES = ("bullish", "bearish", "mixed")


def qqq_regime(row: Mapping[str, Any]) -> str:
    short = float(row.get("technical_benchmark_return_20d_pct") or 0.0)
    long = float(row.get("technical_benchmark_return_60d_pct") or 0.0)
    if short > 0.0 and long > 0.0:
        return "bullish"
    if short <= 0.0 and long <= 0.0:
        return "bearish"
    return "mixed"


def choose_regime_candidate(
    candidates: Sequence[Mapping[str, Any]],
    minimum_signals: int,
) -> Mapping[str, Any]:
    eligible = [
        row for row in candidates
        if int(row["signals"]) >= minimum_signals
        and float(row["mean_net_return_pct"]) > 0.0
        and float(row["median_net_return_pct"]) > 0.0
        and float(row["net_win_rate_pct"]) >= 50.0
        and float(row["tie_expansion_ratio"]) <= 1.5
    ]
    if not eligible:
        raise ValueError("no regime candidate passes validation gates")
    return max(
        eligible,
        key=lambda row: (
            float(row["mean_net_return_pct"]),
            float(row["median_net_return_pct"]),
            -float(row["fraction"]),
        ),
    )


def fit_classifier(
    x: np.ndarray,
    returns: np.ndarray,
    train_idx: np.ndarray,
    validation_idx: np.ndarray,
    feature_names: Sequence[str],
    winner_return_pct: float,
    rounds: int,
    early_stopping: int,
) -> lgb.Booster:
    labels = (returns >= winner_return_pct).astype(np.int32)
    train = lgb.Dataset(
        x[train_idx], label=labels[train_idx], feature_name=list(feature_names)
    )
    validation = lgb.Dataset(
        x[validation_idx],
        label=labels[validation_idx],
        reference=train,
        feature_name=list(feature_names),
    )
    return lgb.train(
        {
            "objective": "binary",
            "metric": ["binary_logloss", "auc"],
            "learning_rate": 0.025,
            "num_leaves": 31,
            "min_data_in_leaf": 75,
            "feature_fraction": 0.85,
            "lambda_l1": 2.0,
            "lambda_l2": 8.0,
            "verbosity": -1,
            "seed": 42,
            "force_col_wise": True,
        },
        train,
        num_boost_round=rounds,
        valid_sets=[validation],
        callbacks=[
            lgb.early_stopping(early_stopping, verbose=False),
            lgb.log_evaluation(0),
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--winner-return-pct", type=float, default=10.0)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    parser.add_argument("--fractions", type=float, nargs="+", default=[0.005, 0.01, 0.02])
    parser.add_argument("--minimum-validation-signals", type=int, default=15)
    parser.add_argument("--max-open-positions", type=int, default=5)
    parser.add_argument("--train-fraction", type=float, default=0.60)
    parser.add_argument("--validation-fraction", type=float, default=0.20)
    parser.add_argument("--embargo-calendar-days", type=int, default=12)
    parser.add_argument("--num-boost-round", type=int, default=800)
    parser.add_argument("--early-stopping-rounds", type=int, default=60)
    args = parser.parse_args()

    rows = [
        {**row, "qqq_regime": qqq_regime(row)}
        for row in read_jsonl(args.rows)
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
    args.output_dir.mkdir(parents=True, exist_ok=True)
    diagnostics, models = [], {}
    validation_set = set(int(index) for index in validation_idx)
    train_set = set(int(index) for index in train_idx)
    for regime in REGIMES:
        regime_train = np.asarray(
            [i for i, row in enumerate(rows) if i in train_set and row["qqq_regime"] == regime]
        )
        regime_validation = np.asarray(
            [i for i, row in enumerate(rows) if i in validation_set and row["qqq_regime"] == regime]
        )
        if len(regime_train) < 500 or len(regime_validation) < 100:
            continue
        model = fit_classifier(
            x,
            returns,
            regime_train,
            regime_validation,
            names,
            args.winner_return_pct,
            args.num_boost_round,
            args.early_stopping_rounds,
        )
        models[regime] = model
        scores = model.predict(
            x[regime_validation], num_iteration=model.best_iteration
        )
        validation_rows = [rows[index] for index in regime_validation]
        for fraction in args.fractions:
            intended = max(1, int(len(scores) * fraction))
            cutoff = float(np.quantile(scores, 1.0 - fraction))
            selected = [
                row for row, score in zip(validation_rows, scores) if float(score) >= cutoff
            ]
            diagnostics.append({
                "regime": regime,
                "fraction": float(fraction),
                "cutoff": cutoff,
                "intended_signals": intended,
                "tie_expansion_ratio": round(len(selected) / intended, 6),
                "train_rows": len(regime_train),
                "validation_rows": len(regime_validation),
                "best_iteration": int(model.best_iteration),
                **trade_metrics(selected, args.round_trip_cost_pct),
            })
    winner = choose_regime_candidate(diagnostics, args.minimum_validation_signals)
    selected_regime = str(winner["regime"])
    selected_model = models[selected_regime]
    selected_model_path = args.output_dir / f"{selected_regime}_classifier.txt"
    selected_model.save_model(
        str(selected_model_path), num_iteration=selected_model.best_iteration
    )
    test_candidates_idx = np.asarray([
        int(index) for index in test_idx
        if rows[int(index)]["qqq_regime"] == selected_regime
    ])
    test_scores = selected_model.predict(
        x[test_candidates_idx], num_iteration=selected_model.best_iteration
    )
    candidates = [
        {**rows[index], "technical_context_score": float(score)}
        for index, score in zip(test_candidates_idx, test_scores)
        if float(score) >= float(winner["cutoff"])
    ]
    selected = capacity_limited(candidates, args.max_open_positions)
    report = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "warning": "The confirmation period was used by earlier Nasdaq studies and is not a fresh untouched test.",
        "regime_contract": {
            "bullish": "QQQ 20-session return > 0 and QQQ 60-session return > 0",
            "bearish": "QQQ 20-session return <= 0 and QQQ 60-session return <= 0",
            "mixed": "all other combinations",
        },
        "selection_contract": "regime, fraction, and cutoff selected from validation only",
        "artifacts": {
            "rows_sha256": file_sha256(args.rows),
            "daily_archive_sha256": daily_archive_sha256(args.daily_dir),
        },
        "settings": {
            "candidate_regimes": list(REGIMES),
            "candidate_fractions": args.fractions,
            "minimum_validation_signals": args.minimum_validation_signals,
            "max_open_positions": args.max_open_positions,
            "round_trip_cost_pct": args.round_trip_cost_pct,
        },
        "split": split,
        "validation_diagnostics": diagnostics,
        "selected": dict(winner),
        "historical_confirmation_regime_rows": len(test_candidates_idx),
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
        "selected_model_path": str(selected_model_path),
    }
    report_path = args.output_dir / "regime_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
