from __future__ import annotations

"""Train the AI/semi 09:30-entry to following-close isolated clone."""

import argparse
import json
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
)


TARGET = "label_next_complete_session_close_net_pct"
FRACTIONS = (0.10, 0.20, 0.30, 0.50)
MAXIMUM_DAILY_SELECTIONS = 5


def scan_dates(path: Path) -> list[str]:
    dates = set()
    with path.open("rb") as handle:
        for line in handle:
            match = DATE_PATTERN.search(line)
            if match is None:
                raise ValueError("panel row missing compact market_date")
            dates.add(match.group(1).decode("ascii"))
    if len(dates) < 50:
        raise ValueError("insufficient market dates")
    return sorted(dates)


def split_dates(dates: Sequence[str]) -> dict[str, list[str]]:
    count = len(dates)
    train_end = int(count * 0.45)
    fit_end = int(count * 0.65)
    policy_end = int(count * 0.82)
    output = {
        "technical_train": list(dates[:train_end]),
        "train_fit_embargo": [dates[train_end]],
        "technical_fit_validation": list(
            dates[train_end + 1 : fit_end]
        ),
        "fit_policy_embargo": [dates[fit_end]],
        "policy_validation": list(dates[fit_end + 1 : policy_end]),
        "policy_test_embargo": [dates[policy_end]],
        "sealed_test": list(dates[policy_end + 1 :]),
    }
    if min(len(output[name]) for name in (
        "technical_train",
        "technical_fit_validation",
        "policy_validation",
        "sealed_test",
    )) < 8:
        raise ValueError("four-stage chronological split is too small")
    return output


def source_feature_names(report: Mapping[str, Any]) -> list[str]:
    names = [
        str(name)
        for name in report.get("feature_names") or []
        if str(name).startswith(
            ("technical_", "model_premarket_", "model_call_")
        )
    ]
    if len(names) != len(report.get("feature_names") or []) or not names:
        raise ValueError("source report feature family drift")
    return names


def select_daily(
    rows: Sequence[Mapping[str, Any]],
    scores: Sequence[float],
    fraction: float,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row, score in zip(rows, scores):
        grouped[str(row["market_date"])].append(
            {**row, "model_score": float(score)}
        )
    selected = []
    for day in sorted(grouped):
        ranked = sorted(
            grouped[day],
            key=lambda row: (-float(row["model_score"]), row["symbol"]),
        )
        count = min(
            MAXIMUM_DAILY_SELECTIONS,
            max(1, int(np.ceil(len(ranked) * fraction))),
        )
        selected.extend(ranked[:count])
    return selected


def metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = np.asarray([float(row[TARGET]) for row in rows], dtype=float)
    dates = len({str(row["market_date"]) for row in rows})
    if len(values) == 0:
        return {
            "signals": 0,
            "decision_dates": 0,
            "mean_net_return_pct": None,
            "median_net_return_pct": None,
            "win_rate_pct": None,
            "fifth_percentile_net_return_pct": None,
        }
    return {
        "signals": int(len(values)),
        "decision_dates": dates,
        "mean_net_return_pct": round(float(np.mean(values)), 6),
        "median_net_return_pct": round(float(np.median(values)), 6),
        "win_rate_pct": round(float(np.mean(values > 0.0) * 100.0), 4),
        "fifth_percentile_net_return_pct": round(
            float(np.percentile(values, 5)), 6
        ),
    }


def diagnostics(
    rows: Sequence[Mapping[str, Any]], scores: Sequence[float]
) -> list[dict[str, Any]]:
    return [
        {
            "fraction": fraction,
            **metrics(select_daily(rows, scores, fraction)),
        }
        for fraction in FRACTIONS
    ]


def choose_policy(
    rows: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    eligible = [
        row
        for row in rows
        if passes_quality_gate(row)
    ]
    return (
        max(
            eligible,
            key=lambda row: (
                float(row["mean_net_return_pct"]),
                float(row["win_rate_pct"]),
                -float(row["fraction"]),
            ),
        )
        if eligible
        else None
    )


def passes_quality_gate(row: Mapping[str, Any]) -> bool:
    return bool(
        int(row["signals"]) >= 30
        and int(row["decision_dates"]) >= 10
        and float(row["mean_net_return_pct"]) > 0.0
        and float(row["median_net_return_pct"]) > 0.0
        and float(row["win_rate_pct"]) >= 50.0
        and float(row["fifth_percentile_net_return_pct"]) >= -10.0
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-training-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError("model output directory must be new")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "complete"
        or manifest.get("clone_model_id")
        != "ai_semiconductor_calls_next_session_close_v1"
        or manifest.get("provider_contract")
        != (
            "Alpha Vantage intraday entry plus Alpha Vantage daily exit; "
            "no provider splicing"
        )
        or manifest.get("panel_sha256") != file_sha256(args.input)
    ):
        raise ValueError("invalid AI/semi next-session panel manifest")
    source_report = json.loads(
        args.source_training_report.read_text(encoding="utf-8")
    )
    names = source_feature_names(source_report)
    splits = split_dates(scan_dates(args.input))
    train_rows = read_rows_for_dates(args.input, splits["technical_train"])
    fit_rows = read_rows_for_dates(
        args.input, splits["technical_fit_validation"]
    )
    x_train = matrix(train_rows, names)
    x_fit = matrix(fit_rows, names)
    y_train = np.asarray(
        [float(row[TARGET]) > 0.0 for row in train_rows], dtype=np.int32
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
            "num_leaves": 15,
            "min_data_in_leaf": 20,
            "feature_fraction": 1.0,
            "lambda_l1": 2.0,
            "lambda_l2": 8.0,
            "verbosity": -1,
            "seed": 42,
            "force_col_wise": True,
            "num_threads": -1,
        },
        train_set,
        num_boost_round=500,
        valid_sets=[fit_set],
        valid_names=["fit_validation"],
        callbacks=[
            lgb.early_stopping(40, verbose=False),
            lgb.log_evaluation(0),
        ],
    )
    policy_rows = read_rows_for_dates(
        args.input, splits["policy_validation"]
    )
    policy_scores = model.predict(
        matrix(policy_rows, names), num_iteration=model.best_iteration
    )
    policy_diagnostics = diagnostics(policy_rows, policy_scores)
    selected_policy = choose_policy(policy_diagnostics)
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
        test_picks = select_daily(
            test_rows, test_scores, float(selected_policy["fraction"])
        )
        test_metrics = metrics(test_picks)
        test_passed = passes_quality_gate(test_metrics)
        status = (
            "FROZEN_PENDING_PROSPECTIVE"
            if test_passed
            else "RESEARCH_HOLD"
        )
        test = {
            "status": "OPENED_ONCE_AFTER_VALIDATION_PASS",
            "json_parsed": True,
            **test_metrics,
            "passed": test_passed,
        }

    args.output_dir.mkdir(parents=True)
    model_path = args.output_dir / "model.txt"
    model.save_model(str(model_path), num_iteration=model.best_iteration)
    report = {
        "status": status,
        "research_only": True,
        "execution_enabled": False,
        "source_model_id": manifest["source_model_id"],
        "clone_model_id": manifest["clone_model_id"],
        "target": TARGET,
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
            "train_rows": len(train_rows),
            "fit_validation_rows": len(fit_rows),
            "train_positive_rate": round(float(np.mean(y_train)), 6),
            "fit_validation_positive_rate": round(
                float(np.mean(y_fit)), 6
            ),
        },
        "policy_validation": {
            "diagnostics": policy_diagnostics,
            "selected": dict(selected_policy) if selected_policy else None,
            "passed": selected_policy is not None,
        },
        "test": test,
        "panel_path": str(args.input),
        "panel_sha256": file_sha256(args.input),
        "manifest_path": str(args.manifest),
        "manifest_sha256": file_sha256(args.manifest),
        "source_training_report_path": str(args.source_training_report),
        "source_training_report_sha256": file_sha256(
            args.source_training_report
        ),
        "model_path": str(model_path),
        "model_sha256": file_sha256(model_path),
        "warnings": [
            "fixed contemporary universe creates survivorship bias",
            "historical passage alone cannot authorize trading",
            "source-model weights and threshold were not inherited",
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
                "policy": report["policy_validation"],
                "test": test,
                "output": str(report_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
