from __future__ import annotations

"""Train calibrated lower/upper daily barrier-probability bounds."""

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.research.barrier_probability_model import (
    FEATURE_NAMES,
    project_probability_bounds,
)
from alientai_v2.research.score_calibration import (
    expected_calibration_error,
    fit_isotonic,
)


DEVELOPMENT_STAGES = (
    "train",
    "fit_validation",
    "calibration",
    "policy_validation",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def matrix(rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    values = np.asarray(
        [
            [float(row[name]) for name in FEATURE_NAMES]
            for row in rows
        ],
        dtype=np.float32,
    )
    if not np.all(np.isfinite(values)):
        raise ValueError("non-finite feature entered training matrix")
    return values


def labels(
    rows: Sequence[Mapping[str, Any]],
    field: str,
) -> np.ndarray:
    output = np.asarray([int(row[field]) for row in rows], dtype=np.int8)
    if set(output.tolist()) - {0, 1}:
        raise ValueError(f"invalid binary labels for {field}")
    return output


def apply_isotonic(
    scores: np.ndarray,
    blocks: Sequence[Mapping[str, float]],
) -> np.ndarray:
    uppers = np.asarray(
        [float(block["upper_score"]) for block in blocks],
        dtype=float,
    )
    probabilities = np.asarray(
        [float(block["probability"]) for block in blocks],
        dtype=float,
    )
    indices = np.searchsorted(uppers, scores.astype(float), side="left")
    return probabilities[np.minimum(indices, len(probabilities) - 1)]


def fit_head(
    train_x: np.ndarray,
    train_y: np.ndarray,
    fit_x: np.ndarray,
    fit_y: np.ndarray,
    *,
    seed: int,
) -> lgb.Booster:
    train_data = lgb.Dataset(
        train_x,
        label=train_y,
        feature_name=list(FEATURE_NAMES),
    )
    fit_data = lgb.Dataset(
        fit_x,
        label=fit_y,
        reference=train_data,
        feature_name=list(FEATURE_NAMES),
    )
    return lgb.train(
        {
            "objective": "binary",
            "metric": ["binary_logloss", "auc"],
            "learning_rate": 0.02,
            "num_leaves": 15,
            "min_data_in_leaf": 120,
            "feature_fraction": 0.85,
            "bagging_fraction": 0.85,
            "bagging_freq": 1,
            "lambda_l1": 3.0,
            "lambda_l2": 12.0,
            "max_depth": 6,
            "verbosity": -1,
            "seed": seed,
            "num_threads": 8,
            "force_col_wise": True,
        },
        train_data,
        num_boost_round=800,
        valid_sets=[fit_data],
        callbacks=[
            lgb.early_stopping(60, verbose=False),
            lgb.log_evaluation(0),
        ],
    )


def safe_auc(y: np.ndarray, probabilities: np.ndarray) -> float | None:
    positives = int(np.sum(y == 1))
    negatives = int(np.sum(y == 0))
    if positives == 0 or negatives == 0:
        return None
    order = np.argsort(probabilities, kind="mergesort")
    ranks = np.empty(len(probabilities), dtype=float)
    start = 0
    while start < len(order):
        end = start + 1
        while (
            end < len(order)
            and probabilities[order[end]] == probabilities[order[start]]
        ):
            end += 1
        average_rank = (start + 1 + end) / 2.0
        ranks[order[start:end]] = average_rank
        start = end
    positive_rank_sum = float(np.sum(ranks[y == 1]))
    return (
        positive_rank_sum - positives * (positives + 1) / 2.0
    ) / (positives * negatives)


def clustered_improvement_interval(
    rows: Sequence[Mapping[str, Any]],
    labels_: np.ndarray,
    probabilities: np.ndarray,
    baseline_probability: float,
    *,
    seed: int = 20260807,
    samples: int = 2000,
) -> tuple[float | None, float | None]:
    by_date: dict[str, list[float]] = defaultdict(list)
    for row, label, probability in zip(rows, labels_, probabilities):
        baseline_error = (float(label) - baseline_probability) ** 2
        model_error = (float(label) - float(probability)) ** 2
        by_date[str(row["market_date"])].append(
            baseline_error - model_error
        )
    date_means = np.asarray(
        [float(np.mean(values)) for values in by_date.values()],
        dtype=float,
    )
    if len(date_means) < 2:
        return None, None
    generator = np.random.default_rng(seed)
    draws = generator.choice(
        date_means,
        size=(samples, len(date_means)),
        replace=True,
    ).mean(axis=1)
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def probability_metrics(
    rows: Sequence[Mapping[str, Any]],
    labels_: np.ndarray,
    probabilities: np.ndarray,
    *,
    baseline_probability: float,
    top_threshold: float,
) -> dict[str, Any]:
    baseline_probability = float(
        np.clip(baseline_probability, 1e-6, 1.0 - 1e-6)
    )
    probabilities = np.clip(probabilities.astype(float), 1e-6, 1.0 - 1e-6)
    brier = float(np.mean((labels_ - probabilities) ** 2))
    baseline_brier = float(
        np.mean((labels_ - baseline_probability) ** 2)
    )
    selected = probabilities >= float(top_threshold)
    ci_low, ci_high = clustered_improvement_interval(
        rows,
        labels_,
        probabilities,
        baseline_probability,
    )
    dates = {str(row["market_date"]) for row in rows}
    return {
        "rows": len(rows),
        "decision_dates": len(dates),
        "positive_rate": round(float(np.mean(labels_)), 8),
        "mean_probability": round(float(np.mean(probabilities)), 8),
        "auc": (
            round(float(safe_auc(labels_, probabilities)), 8)
            if safe_auc(labels_, probabilities) is not None
            else None
        ),
        "brier": round(brier, 8),
        "baseline_brier": round(baseline_brier, 8),
        "brier_skill_pct": (
            round((baseline_brier - brier) / baseline_brier * 100.0, 6)
            if baseline_brier > 0.0
            else None
        ),
        "log_loss": round(
            float(
                -np.mean(
                    labels_ * np.log(probabilities)
                    + (1 - labels_) * np.log(1.0 - probabilities)
                )
            ),
            8,
        ),
        "expected_calibration_error_10bin": round(
            float(
                expected_calibration_error(
                    probabilities.tolist(),
                    labels_.tolist(),
                    bins=10,
                )
            ),
            8,
        ),
        "date_cluster_brier_improvement_ci95_low": (
            round(ci_low, 8) if ci_low is not None else None
        ),
        "date_cluster_brier_improvement_ci95_high": (
            round(ci_high, 8) if ci_high is not None else None
        ),
        "top_decile_threshold_from_calibration": round(
            float(top_threshold), 8
        ),
        "top_decile_rows": int(np.sum(selected)),
        "top_decile_dates": len(
            {
                str(row["market_date"])
                for row, take in zip(rows, selected)
                if take
            }
        ),
        "top_decile_success_rate": (
            round(float(np.mean(labels_[selected])), 8)
            if np.any(selected)
            else None
        ),
        "top_decile_lift_percentage_points_vs_calibration_base": (
            round(
                (float(np.mean(labels_[selected])) - baseline_probability)
                * 100.0,
                6,
            )
            if np.any(selected)
            else None
        ),
    }


def stage_record(
    manifest: Mapping[str, Any],
    stage: str,
    *,
    loaded: bool,
) -> dict[str, Any]:
    source = manifest["partitions"][stage]
    return {
        "rows": source["rows"],
        "decision_dates": source["decision_dates"],
        "first_decision_date": source["first_decision_date"],
        "last_decision_date": source["last_decision_date"],
        "loaded_by_trainer": loaded,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError("output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = args.panel_dir / "manifest.json"
    audit_path = args.panel_dir / "content_audit.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS" or not audit.get("integrity_pass"):
        raise ValueError("panel content audit must pass before training")
    if audit.get("manifest_sha256") != sha256(manifest_path):
        raise ValueError("panel manifest changed after content audit")
    if not manifest.get("research_only") or manifest.get("execution_enabled"):
        raise ValueError("panel must remain research-only")

    rows = {
        stage: read_jsonl(Path(manifest["partitions"][stage]["path"]))
        for stage in DEVELOPMENT_STAGES
    }
    x = {stage: matrix(values) for stage, values in rows.items()}
    lower_y = {
        stage: labels(values, "label_lower_bound")
        for stage, values in rows.items()
    }
    upper_y = {
        stage: labels(values, "label_upper_bound")
        for stage, values in rows.items()
    }
    lower_model = fit_head(
        x["train"],
        lower_y["train"],
        x["fit_validation"],
        lower_y["fit_validation"],
        seed=20260807,
    )
    upper_model = fit_head(
        x["train"],
        upper_y["train"],
        x["fit_validation"],
        upper_y["fit_validation"],
        seed=20260808,
    )

    lower_calibration_scores = lower_model.predict(
        x["calibration"],
        num_iteration=lower_model.best_iteration,
    )
    upper_calibration_scores = upper_model.predict(
        x["calibration"],
        num_iteration=upper_model.best_iteration,
    )
    lower_blocks = fit_isotonic(
        lower_calibration_scores.tolist(),
        lower_y["calibration"].tolist(),
    )
    upper_blocks = fit_isotonic(
        upper_calibration_scores.tolist(),
        upper_y["calibration"].tolist(),
    )
    lower_calibrated_raw = apply_isotonic(
        lower_calibration_scores,
        lower_blocks,
    )
    upper_calibrated_raw = apply_isotonic(
        upper_calibration_scores,
        upper_blocks,
    )
    lower_calibrated, upper_calibrated, calibration_crossed = (
        project_probability_bounds(
            lower_calibrated_raw,
            upper_calibrated_raw,
        )
    )
    lower_base = float(np.mean(lower_y["calibration"]))
    upper_base = float(np.mean(upper_y["calibration"]))
    lower_top_threshold = float(np.percentile(lower_calibrated, 90.0))
    upper_top_threshold = float(np.percentile(upper_calibrated, 90.0))

    lower_policy_raw = apply_isotonic(
        lower_model.predict(
            x["policy_validation"],
            num_iteration=lower_model.best_iteration,
        ),
        lower_blocks,
    )
    upper_policy_raw = apply_isotonic(
        upper_model.predict(
            x["policy_validation"],
            num_iteration=upper_model.best_iteration,
        ),
        upper_blocks,
    )
    lower_policy, upper_policy, policy_crossed = project_probability_bounds(
        lower_policy_raw,
        upper_policy_raw,
    )
    lower_metrics = probability_metrics(
        rows["policy_validation"],
        lower_y["policy_validation"],
        lower_policy,
        baseline_probability=lower_base,
        top_threshold=lower_top_threshold,
    )
    upper_metrics = probability_metrics(
        rows["policy_validation"],
        upper_y["policy_validation"],
        upper_policy,
        baseline_probability=upper_base,
        top_threshold=upper_top_threshold,
    )
    interval_metrics = {
        "mean_width": round(
            float(np.mean(upper_policy - lower_policy)), 8
        ),
        "median_width": round(
            float(np.median(upper_policy - lower_policy)), 8
        ),
        "p95_width": round(
            float(np.percentile(upper_policy - lower_policy, 95)), 8
        ),
        "pre_projection_crossing_rate": round(
            float(np.mean(policy_crossed)), 8
        ),
        "calibration_pre_projection_crossing_rate": round(
            float(np.mean(calibration_crossed)), 8
        ),
    }

    gates = {
        "minimum_rows": lower_metrics["rows"] >= 5000,
        "minimum_dates": lower_metrics["decision_dates"] >= 60,
        "lower_auc": (
            lower_metrics["auc"] is not None
            and lower_metrics["auc"] >= 0.52
        ),
        "upper_auc": (
            upper_metrics["auc"] is not None
            and upper_metrics["auc"] >= 0.52
        ),
        "lower_positive_brier_skill": (
            lower_metrics["brier_skill_pct"] is not None
            and lower_metrics["brier_skill_pct"] > 0.0
        ),
        "upper_positive_brier_skill": (
            upper_metrics["brier_skill_pct"] is not None
            and upper_metrics["brier_skill_pct"] > 0.0
        ),
        "lower_cluster_ci_positive": (
            lower_metrics[
                "date_cluster_brier_improvement_ci95_low"
            ]
            is not None
            and lower_metrics[
                "date_cluster_brier_improvement_ci95_low"
            ]
            > 0.0
        ),
        "lower_ece": (
            lower_metrics["expected_calibration_error_10bin"] <= 0.05
        ),
        "lower_top_decile_lift": (
            lower_metrics[
                "top_decile_lift_percentage_points_vs_calibration_base"
            ]
            is not None
            and lower_metrics[
                "top_decile_lift_percentage_points_vs_calibration_base"
            ]
            >= 2.0
        ),
        "interval_width": interval_metrics["mean_width"] <= 0.30,
        "crossing_rate": (
            interval_metrics["pre_projection_crossing_rate"] <= 0.05
        ),
    }
    gate_passed = all(gates.values())

    lower_model_path = args.output_dir / "lower_bound_model.txt"
    upper_model_path = args.output_dir / "upper_bound_model.txt"
    lower_model.save_model(
        str(lower_model_path),
        num_iteration=lower_model.best_iteration,
    )
    upper_model.save_model(
        str(upper_model_path),
        num_iteration=upper_model.best_iteration,
    )
    calibration_path = args.output_dir / "calibration.json"
    calibration_path.write_text(
        json.dumps(
            {
                "lower_bound_blocks": lower_blocks,
                "upper_bound_blocks": upper_blocks,
                "lower_calibration_base_rate": lower_base,
                "upper_calibration_base_rate": upper_base,
                "lower_top_decile_threshold": lower_top_threshold,
                "upper_top_decile_threshold": upper_top_threshold,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    test_report: dict[str, Any]
    sealed_test_predictions_path: Path | None = None
    if not gate_passed:
        status = "RESEARCH_HOLD"
        test_report = {
            "status": "SEALED_UNLOADED",
            "reason": "one or more frozen policy-validation gates failed",
            "rows_loaded_by_trainer": False,
        }
    else:
        test_rows = read_jsonl(
            Path(manifest["partitions"]["sealed_test"]["path"])
        )
        test_x = matrix(test_rows)
        test_lower_y = labels(test_rows, "label_lower_bound")
        test_upper_y = labels(test_rows, "label_upper_bound")
        test_lower_raw = apply_isotonic(
            lower_model.predict(
                test_x,
                num_iteration=lower_model.best_iteration,
            ),
            lower_blocks,
        )
        test_upper_raw = apply_isotonic(
            upper_model.predict(
                test_x,
                num_iteration=upper_model.best_iteration,
            ),
            upper_blocks,
        )
        test_lower, test_upper, test_crossed = project_probability_bounds(
            test_lower_raw,
            test_upper_raw,
        )
        test_report = {
            "status": "OPENED_ONCE_AFTER_POLICY_VALIDATION_PASS",
            "rows_loaded_by_trainer": True,
            "lower_bound": probability_metrics(
                test_rows,
                test_lower_y,
                test_lower,
                baseline_probability=lower_base,
                top_threshold=lower_top_threshold,
            ),
            "upper_bound": probability_metrics(
                test_rows,
                test_upper_y,
                test_upper,
                baseline_probability=upper_base,
                top_threshold=upper_top_threshold,
            ),
            "interval": {
                "mean_width": round(
                    float(np.mean(test_upper - test_lower)), 8
                ),
                "pre_projection_crossing_rate": round(
                    float(np.mean(test_crossed)), 8
                ),
            },
        }
        sealed_test_predictions_path = (
            args.output_dir / "sealed_test_predictions.jsonl"
        )
        with sealed_test_predictions_path.open(
            "w", encoding="utf-8", newline="\n"
        ) as handle:
            for row, lower_probability, upper_probability in zip(
                test_rows,
                test_lower,
                test_upper,
            ):
                handle.write(
                    json.dumps(
                        {
                            "market_date": row["market_date"],
                            "symbol": row["symbol"],
                            "conservative_lower_probability": float(
                                lower_probability
                            ),
                            "optimistic_upper_probability": float(
                                upper_probability
                            ),
                            "diagnostic_midpoint_probability": float(
                                (
                                    lower_probability
                                    + upper_probability
                                )
                                / 2.0
                            ),
                            "label_lower_bound": row["label_lower_bound"],
                            "label_upper_bound": row["label_upper_bound"],
                            "execution_decision": "AVOID",
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
        status = "FROZEN_PENDING_PROSPECTIVE_REVIEW"

    feature_importance = sorted(
        [
            {
                "feature": feature,
                "combined_gain": round(float(gain), 6),
            }
            for feature, gain in zip(
                FEATURE_NAMES,
                lower_model.feature_importance(importance_type="gain")
                + upper_model.feature_importance(importance_type="gain"),
            )
        ],
        key=lambda item: item["combined_gain"],
        reverse=True,
    )
    report = {
        "status": status,
        "research_only": True,
        "execution_enabled": False,
        "execution_decision": "AVOID",
        "model_id": manifest["model_id"],
        "question": (
            "probability bounds for reaching +1.5% before -0.5% from "
            "the next regular-session open within ten sessions"
        ),
        "provider": manifest["provider"],
        "universe": manifest["symbols"],
        "universe_count": manifest["symbol_count"],
        "features": list(FEATURE_NAMES),
        "entry": manifest["entry"],
        "barriers": {
            "upper_pct": manifest["upper_barrier_pct"],
            "lower_pct": manifest["lower_barrier_pct"],
            "maximum_horizon_sessions": (
                manifest["maximum_horizon_sessions"]
            ),
            "timeout": "failure",
            "same_session_double_touch": (
                "lower head=failure; upper head=success"
            ),
        },
        "panel_manifest_path": str(manifest_path.resolve()),
        "panel_manifest_sha256": sha256(manifest_path),
        "panel_audit_path": str(audit_path.resolve()),
        "panel_audit_sha256": sha256(audit_path),
        "partitions": {
            stage: stage_record(manifest, stage, loaded=True)
            for stage in DEVELOPMENT_STAGES
        }
        | {
            "sealed_test": stage_record(
                manifest,
                "sealed_test",
                loaded=gate_passed,
            )
        },
        "embargo_sessions_each_side": (
            manifest["embargo_sessions_each_side"]
        ),
        "lower_model_path": str(lower_model_path.resolve()),
        "lower_model_sha256": sha256(lower_model_path),
        "lower_model_best_iteration": int(lower_model.best_iteration),
        "upper_model_path": str(upper_model_path.resolve()),
        "upper_model_sha256": sha256(upper_model_path),
        "upper_model_best_iteration": int(upper_model.best_iteration),
        "calibration_path": str(calibration_path.resolve()),
        "calibration_sha256": sha256(calibration_path),
        "calibration_base_rates": {
            "lower_bound": lower_base,
            "upper_bound": upper_base,
        },
        "policy_validation": {
            "lower_bound": lower_metrics,
            "upper_bound": upper_metrics,
            "interval": interval_metrics,
            "frozen_gates": gates,
            "all_gates_passed": gate_passed,
        },
        "sealed_test": test_report,
        "sealed_test_predictions_path": (
            str(sealed_test_predictions_path.resolve())
            if sealed_test_predictions_path
            else None
        ),
        "sealed_test_predictions_sha256": (
            sha256(sealed_test_predictions_path)
            if sealed_test_predictions_path
            else None
        ),
        "top_features": feature_importance,
        "warnings": manifest["warnings"],
        "interpretation": (
            "the conservative lower probability is the only headline "
            "probability; the midpoint is diagnostic and no trade policy "
            "has been validated"
        ),
    }
    report_path = args.output_dir / "training_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": status,
                "policy_validation_passed": gate_passed,
                "failed_gates": [
                    name for name, passed in gates.items() if not passed
                ],
                "lower_bound": lower_metrics,
                "upper_bound": upper_metrics,
                "interval": interval_metrics,
                "sealed_test_status": test_report["status"],
                "report": str(report_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
