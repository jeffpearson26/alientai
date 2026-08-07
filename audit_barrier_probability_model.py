from __future__ import annotations

"""Independently verify barrier text models, probabilities, and gate state."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.research.barrier_probability_model import (
    FEATURE_NAMES,
    project_probability_bounds,
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
    return np.asarray(
        [[float(row[name]) for name in FEATURE_NAMES] for row in rows],
        dtype=np.float32,
    )


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


def auc(labels: np.ndarray, scores: np.ndarray) -> float:
    positives = int(np.sum(labels == 1))
    negatives = int(np.sum(labels == 0))
    if positives == 0 or negatives == 0:
        raise ValueError("AUC requires both classes")
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=float)
    start = 0
    while start < len(order):
        end = start + 1
        while (
            end < len(order)
            and scores[order[end]] == scores[order[start]]
        ):
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    return (
        float(np.sum(ranks[labels == 1]))
        - positives * (positives + 1) / 2.0
    ) / (positives * negatives)


def ece(labels: np.ndarray, probabilities: np.ndarray) -> float:
    total = len(labels)
    result = 0.0
    for index in range(10):
        lower = index / 10.0
        upper = (index + 1) / 10.0
        selected = (probabilities >= lower) & (
            (probabilities < upper)
            | ((index == 9) & (probabilities == 1.0))
        )
        if not np.any(selected):
            continue
        result += (
            float(np.sum(selected))
            / total
            * abs(
                float(np.mean(probabilities[selected]))
                - float(np.mean(labels[selected]))
            )
        )
    return result


def core_metrics(
    rows: Sequence[Mapping[str, Any]],
    label_field: str,
    probabilities: np.ndarray,
    *,
    base_rate: float,
    top_threshold: float,
) -> dict[str, float | int]:
    labels = np.asarray([int(row[label_field]) for row in rows], dtype=int)
    probabilities = np.clip(probabilities, 1e-6, 1.0 - 1e-6)
    brier = float(np.mean((labels - probabilities) ** 2))
    baseline = float(np.mean((labels - base_rate) ** 2))
    selected = probabilities >= top_threshold
    return {
        "rows": len(rows),
        "positive_rate": float(np.mean(labels)),
        "auc": auc(labels, probabilities),
        "brier": brier,
        "baseline_brier": baseline,
        "brier_skill_pct": (baseline - brier) / baseline * 100.0,
        "expected_calibration_error_10bin": ece(labels, probabilities),
        "top_decile_rows": int(np.sum(selected)),
        "top_decile_success_rate": float(np.mean(labels[selected])),
        "top_decile_lift_percentage_points_vs_calibration_base": (
            float(np.mean(labels[selected])) - base_rate
        )
        * 100.0,
    }


def compare_metrics(
    observed: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    prefix: str,
    errors: list[str],
) -> None:
    for name, value in expected.items():
        if name not in observed:
            errors.append(f"{prefix}: missing metric {name}")
            continue
        if isinstance(value, int):
            if int(observed[name]) != value:
                errors.append(f"{prefix}: {name} mismatch")
        elif not math.isclose(
            float(observed[name]),
            float(value),
            rel_tol=1e-6,
            abs_tol=1e-6,
        ):
            errors.append(f"{prefix}: {name} mismatch")


def audit(model_dir: Path) -> dict[str, Any]:
    report_path = model_dir / "training_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if (
        not report.get("research_only")
        or report.get("execution_enabled")
        or report.get("execution_decision") != "AVOID"
    ):
        errors.append("research/execution guard mismatch")

    panel_manifest_path = Path(report["panel_manifest_path"])
    panel_audit_path = Path(report["panel_audit_path"])
    if sha256(panel_manifest_path) != report["panel_manifest_sha256"]:
        errors.append("panel manifest hash mismatch")
    if sha256(panel_audit_path) != report["panel_audit_sha256"]:
        errors.append("panel audit hash mismatch")
    panel_audit = json.loads(panel_audit_path.read_text(encoding="utf-8"))
    if panel_audit.get("status") != "PASS":
        errors.append("panel audit no longer passes")
    manifest = json.loads(panel_manifest_path.read_text(encoding="utf-8"))

    lower_path = Path(report["lower_model_path"])
    upper_path = Path(report["upper_model_path"])
    calibration_path = Path(report["calibration_path"])
    for name, path, expected_hash in (
        ("lower model", lower_path, report["lower_model_sha256"]),
        ("upper model", upper_path, report["upper_model_sha256"]),
        ("calibration", calibration_path, report["calibration_sha256"]),
    ):
        if sha256(path) != expected_hash:
            errors.append(f"{name} hash mismatch")
    lower_model = lgb.Booster(model_file=str(lower_path))
    upper_model = lgb.Booster(model_file=str(upper_path))
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))

    rescored: dict[str, dict[str, Any]] = {}
    probabilities_by_stage: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for stage in ("policy_validation", "sealed_test"):
        rows = read_jsonl(Path(manifest["partitions"][stage]["path"]))
        values = matrix(rows)
        lower_raw = apply_isotonic(
            lower_model.predict(values),
            calibration["lower_bound_blocks"],
        )
        upper_raw = apply_isotonic(
            upper_model.predict(values),
            calibration["upper_bound_blocks"],
        )
        lower, upper, crossed = project_probability_bounds(
            lower_raw,
            upper_raw,
        )
        probabilities_by_stage[stage] = (lower, upper)
        lower_metrics = core_metrics(
            rows,
            "label_lower_bound",
            lower,
            base_rate=float(calibration["lower_calibration_base_rate"]),
            top_threshold=float(
                calibration["lower_top_decile_threshold"]
            ),
        )
        upper_metrics = core_metrics(
            rows,
            "label_upper_bound",
            upper,
            base_rate=float(calibration["upper_calibration_base_rate"]),
            top_threshold=float(
                calibration["upper_top_decile_threshold"]
            ),
        )
        rescored[stage] = {
            "rows": len(rows),
            "lower_bound": lower_metrics,
            "upper_bound": upper_metrics,
            "interval_mean_width": float(np.mean(upper - lower)),
            "pre_projection_crossing_rate": float(np.mean(crossed)),
        }
        expected_section = (
            report["policy_validation"]
            if stage == "policy_validation"
            else report["sealed_test"]
        )
        compare_metrics(
            expected_section["lower_bound"],
            lower_metrics,
            prefix=f"{stage} lower",
            errors=errors,
        )
        compare_metrics(
            expected_section["upper_bound"],
            upper_metrics,
            prefix=f"{stage} upper",
            errors=errors,
        )

    gates = report["policy_validation"]["frozen_gates"]
    if not all(bool(value) for value in gates.values()):
        errors.append("report opened the test without all gates passing")
    if (
        report.get("status") != "FROZEN_PENDING_PROSPECTIVE_REVIEW"
        or report["sealed_test"].get("status")
        != "OPENED_ONCE_AFTER_POLICY_VALIDATION_PASS"
    ):
        errors.append("unexpected frozen/test status")

    predictions_path = Path(report["sealed_test_predictions_path"])
    if sha256(predictions_path) != report["sealed_test_predictions_sha256"]:
        errors.append("sealed prediction hash mismatch")
    prediction_rows = read_jsonl(predictions_path)
    test_rows = read_jsonl(
        Path(manifest["partitions"]["sealed_test"]["path"])
    )
    lower_test, upper_test = probabilities_by_stage["sealed_test"]
    if len(prediction_rows) != len(test_rows):
        errors.append("sealed prediction row count mismatch")
    else:
        seen: set[tuple[str, str]] = set()
        for source, prediction, lower, upper in zip(
            test_rows,
            prediction_rows,
            lower_test,
            upper_test,
        ):
            key = (str(prediction["symbol"]), str(prediction["market_date"]))
            if key in seen:
                errors.append(f"duplicate sealed prediction {key}")
                break
            seen.add(key)
            if key != (str(source["symbol"]), str(source["market_date"])):
                errors.append("sealed prediction key mismatch")
                break
            if prediction.get("execution_decision") != "AVOID":
                errors.append("sealed prediction execution guard mismatch")
                break
            if not math.isclose(
                float(prediction["conservative_lower_probability"]),
                float(lower),
                rel_tol=1e-10,
                abs_tol=1e-10,
            ) or not math.isclose(
                float(prediction["optimistic_upper_probability"]),
                float(upper),
                rel_tol=1e-10,
                abs_tol=1e-10,
            ):
                errors.append("sealed prediction probability mismatch")
                break

    return {
        "status": "PASS" if not errors else "FAIL",
        "integrity_pass": not errors,
        "research_only": True,
        "execution_enabled": False,
        "model_id": report.get("model_id"),
        "report_path": str(report_path.resolve()),
        "report_sha256": sha256(report_path),
        "lower_model_trees": lower_model.num_trees(),
        "upper_model_trees": upper_model.num_trees(),
        "rescored": rescored,
        "sealed_predictions_verified": len(prediction_rows),
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.model_dir)
    output = args.output or args.model_dir / "independent_model_audit.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "sealed_predictions_verified": (
                    result["sealed_predictions_verified"]
                ),
                "errors": result["errors"],
                "output": str(output),
            },
            indent=2,
        )
    )
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
