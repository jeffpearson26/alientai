from __future__ import annotations

"""Train a Nasdaq technical clone with an independently sealed one-day test."""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from train_contextual_options_next_session_clone import (
    DATE_PATTERN,
    file_sha256,
    matrix,
    read_rows_for_dates,
    technical_feature_names,
)


TARGET = "label_forward_return_1d_pct"
FRACTIONS = (0.0025, 0.005, 0.01)
MINIMUM_VALIDATION_SIGNALS = 20
MAXIMUM_DAILY_SELECTIONS = 5


def scan_dates(path: Path) -> list[str]:
    dates = set()
    with path.open("rb") as handle:
        for line in handle:
            match = DATE_PATTERN.search(line)
            if match is None:
                raise ValueError("panel row missing compact market_date")
            dates.add(match.group(1).decode("ascii"))
    if len(dates) < 80:
        raise ValueError("insufficient market dates")
    return sorted(dates)


def split_dates(dates: Sequence[str]) -> dict[str, list[str]]:
    """Create four chronological stages with one decision-date embargoes."""
    count = len(dates)
    train_end = int(count * 0.50)
    fit_end = int(count * 0.70)
    policy_end = int(count * 0.85)
    train = list(dates[:train_end])
    fit = list(dates[train_end + 1 : fit_end])
    policy = list(dates[fit_end + 1 : policy_end])
    test = list(dates[policy_end + 1 :])
    if min(map(len, (train, fit, policy, test))) < 10:
        raise ValueError("four-stage chronological split is too small")
    return {
        "technical_train": train,
        "train_fit_embargo": [dates[train_end]],
        "technical_fit_validation": fit,
        "fit_policy_embargo": [dates[fit_end]],
        "policy_validation": policy,
        "policy_test_embargo": [dates[policy_end]],
        "sealed_test": test,
    }


def select_daily(
    rows: Sequence[Mapping[str, Any]],
    scores: Sequence[float],
    cutoff: float,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row, score in zip(rows, scores):
        if float(score) >= cutoff:
            grouped[str(row["market_date"])].append(
                {**row, "model_score": float(score)}
            )
    return [
        row
        for day in sorted(grouped)
        for row in sorted(
            grouped[day],
            key=lambda item: (-float(item["model_score"]), item["symbol"]),
        )[:MAXIMUM_DAILY_SELECTIONS]
    ]


def metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = [float(row[TARGET]) for row in rows]
    daily: dict[str, list[float]] = defaultdict(list)
    for row, value in zip(rows, values):
        daily[str(row["market_date"])].append(value)
    equity = peak = 1.0
    worst = 0.0
    for day in sorted(daily):
        # Unused slots remain cash.
        equity *= 1.0 + (
            sum(daily[day]) / MAXIMUM_DAILY_SELECTIONS
        ) / 100.0
        peak = max(peak, equity)
        worst = min(worst, (equity / peak - 1.0) * 100.0)
    return {
        "signals": len(values),
        "decision_dates": len(daily),
        "mean_net_return_pct": round(mean(values), 6) if values else None,
        "median_net_return_pct": (
            round(median(values), 6) if values else None
        ),
        "win_rate_pct": (
            round(mean(value > 0.0 for value in values) * 100.0, 4)
            if values
            else None
        ),
        "capital_scaled_return_pct": round((equity - 1.0) * 100.0, 6),
        "capital_scaled_max_drawdown_pct": round(worst, 6),
    }


def policy_diagnostics(
    rows: Sequence[Mapping[str, Any]], scores: Sequence[float]
) -> list[dict[str, Any]]:
    score_array = np.asarray(scores, dtype=float)
    output = []
    for fraction in FRACTIONS:
        cutoff = float(np.quantile(score_array, 1.0 - fraction))
        intended = max(1, math.ceil(len(rows) * fraction))
        candidates = sum(float(score) >= cutoff for score in scores)
        selected = select_daily(rows, scores, cutoff)
        result = metrics(selected)
        output.append(
            {
                "fraction": fraction,
                "cutoff": cutoff,
                "intended_candidates": intended,
                "candidates_before_daily_cap": candidates,
                "tie_expansion_ratio": round(candidates / intended, 6),
                **result,
            }
        )
    return output


def choose_policy(
    diagnostics: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    eligible = [
        row
        for row in diagnostics
        if int(row["signals"]) >= MINIMUM_VALIDATION_SIGNALS
        and float(row["mean_net_return_pct"]) > 0.0
        and float(row["median_net_return_pct"]) > 0.0
        and float(row["win_rate_pct"]) >= 50.0
        and float(row["tie_expansion_ratio"]) <= 1.5
    ]
    return (
        max(
            eligible,
            key=lambda row: (
                float(row["mean_net_return_pct"]),
                -float(row["fraction"]),
            ),
        )
        if eligible
        else None
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--num-boost-round", type=int, default=800)
    parser.add_argument("--early-stopping-rounds", type=int, default=60)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError("model output directory must be new")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "complete"
        or manifest.get("target_horizon_sessions") != 1
        or manifest.get("round_trip_cost_pct") != 0.25
        or int(manifest.get("universe_count") or 0) < 2
        or manifest.get("panel_sha256") != file_sha256(args.input)
    ):
        raise ValueError("invalid Nasdaq next-session panel manifest")

    splits = split_dates(scan_dates(args.input))
    training_rows = read_rows_for_dates(
        args.input, splits["technical_train"]
    )
    fit_rows = read_rows_for_dates(
        args.input, splits["technical_fit_validation"]
    )
    names = technical_feature_names(training_rows)
    x_train = matrix(training_rows, names)
    x_fit = matrix(fit_rows, names)
    y_train = np.asarray(
        [float(row[TARGET]) > 0.0 for row in training_rows], dtype=np.int32
    )
    y_fit = np.asarray(
        [float(row[TARGET]) > 0.0 for row in fit_rows], dtype=np.int32
    )
    train_set = lgb.Dataset(x_train, label=y_train, feature_name=names)
    fit_set = lgb.Dataset(
        x_fit, label=y_fit, reference=train_set, feature_name=names
    )
    model = lgb.train(
        {
            "objective": "binary",
            "metric": ["binary_logloss", "auc"],
            "learning_rate": 0.025,
            "num_leaves": 31,
            "min_data_in_leaf": 100,
            "feature_fraction": 0.85,
            "lambda_l1": 2.0,
            "lambda_l2": 8.0,
            "verbosity": -1,
            "seed": 42,
            "force_col_wise": True,
            "num_threads": -1,
        },
        train_set,
        num_boost_round=args.num_boost_round,
        valid_sets=[fit_set],
        valid_names=["fit_validation"],
        callbacks=[
            lgb.early_stopping(args.early_stopping_rounds, verbose=False),
            lgb.log_evaluation(0),
        ],
    )

    policy_rows = read_rows_for_dates(
        args.input, splits["policy_validation"]
    )
    policy_scores = model.predict(
        matrix(policy_rows, names), num_iteration=model.best_iteration
    )
    diagnostics = policy_diagnostics(policy_rows, policy_scores)
    selected_policy = choose_policy(diagnostics)
    if selected_policy is None:
        status = "RESEARCH_HOLD"
        test = {
            "status": "SEALED_UNLOADED",
            "json_parsed": False,
            "reason": "no validation fraction passed the frozen quality gate",
        }
    else:
        test_rows = read_rows_for_dates(args.input, splits["sealed_test"])
        test_scores = model.predict(
            matrix(test_rows, names), num_iteration=model.best_iteration
        )
        selected_test = select_daily(
            test_rows, test_scores, float(selected_policy["cutoff"])
        )
        status = "FROZEN_PENDING_PROSPECTIVE"
        test = {
            "status": "OPENED_ONCE_AFTER_VALIDATION_PASS",
            "json_parsed": True,
            **metrics(selected_test),
        }

    args.output_dir.mkdir(parents=True)
    model_path = args.output_dir / "technical_classifier.txt"
    model.save_model(str(model_path), num_iteration=model.best_iteration)
    report = {
        "status": status,
        "research_only": True,
        "execution_enabled": False,
        "source_model_id": manifest["source_model_id"],
        "clone_model_id": manifest["clone_model_id"],
        "target": TARGET,
        "target_definition": (
            "next regular-session open to same-session official close minus "
            "0.25% round-trip cost"
        ),
        "feature_names": names,
        "best_iteration": int(model.best_iteration),
        "split": {
            name: {
                "dates": len(days),
                "first": days[0],
                "last": days[-1],
            }
            for name, days in splits.items()
        },
        "technical_fit": {
            "train_rows": len(training_rows),
            "fit_validation_rows": len(fit_rows),
            "train_positive_rate": round(float(np.mean(y_train)), 6),
            "fit_validation_positive_rate": round(
                float(np.mean(y_fit)), 6
            ),
        },
        "policy_validation": {
            "candidate_fractions": list(FRACTIONS),
            "minimum_signals": MINIMUM_VALIDATION_SIGNALS,
            "maximum_daily_selections": MAXIMUM_DAILY_SELECTIONS,
            "diagnostics": diagnostics,
            "selected": dict(selected_policy) if selected_policy else None,
            "passed": selected_policy is not None,
        },
        "test": test,
        "panel_path": str(args.input),
        "panel_sha256": file_sha256(args.input),
        "manifest_path": str(args.manifest),
        "manifest_sha256": file_sha256(args.manifest),
        "model_path": str(model_path),
        "model_sha256": file_sha256(model_path),
        "warnings": [
            "fixed June 2026 membership creates survivorship bias",
            "historical passage alone cannot authorize trading",
            "source-model evidence is not inherited",
        ],
    }
    report_path = args.output_dir / "training_report.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": status,
                "policy_pass": selected_policy is not None,
                "selected_policy": dict(selected_policy)
                if selected_policy
                else None,
                "test": test,
                "output": str(report_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
