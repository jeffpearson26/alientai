from __future__ import annotations

"""Independently verify the two frozen full-archive training decisions."""

import argparse
import json
from pathlib import Path
from typing import Any

from build_full_archive_multiresolution_technical_panel import MODEL_FAMILY, sha256
from train_full_archive_multiresolution_technical import FEATURE_SETS, MODEL_IDS


def audit_report(path: Path, horizon: int) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    variants = list(report.get("variants") or [])
    passed = [item for item in variants if item.get("validation_passed")]
    expected_variants = {
        (feature_set, algorithm)
        for feature_set in FEATURE_SETS
        for algorithm in ("lightgbm", "xgboost")
    }
    actual_variants = {
        (str(item.get("feature_set")), str(item.get("algorithm")))
        for item in variants
    }
    expected_checks = {
        "minimum_100_signals",
        "minimum_20_dates",
        "positive_mean_net",
        "positive_median_net",
        "win_rate_at_least_50",
        "positive_rank_ic",
        "positive_top_minus_bottom",
        "positive_clustered_lower_95",
    }
    if (
        report.get("model_id") != MODEL_IDS[horizon]
        or report.get("model_family") != MODEL_FAMILY
        or report.get("horizon_sessions") != horizon
        or report.get("research_only") is not True
        or report.get("execution_decision") != "AVOID"
        or report.get("cost_pct") != 0.25
        or actual_variants != expected_variants
    ):
        errors.append("training report frozen contract mismatch")
    for variant in variants:
        selected = variant.get("selected_validation_policy") or {}
        gate = selected.get("gate") or {}
        checks = gate.get("checks") or {}
        if (
            set(checks) != expected_checks
            or
            bool(gate.get("passed")) != all(bool(value) for value in checks.values())
            or bool(variant.get("validation_passed"))
            != bool(gate.get("passed"))
        ):
            errors.append(
                f"validation gate mismatch: "
                f"{variant.get('feature_set')}|{variant.get('algorithm')}"
            )
        artifact = variant.get("oof_artifact") or {}
        oof_path = Path(str(artifact.get("path") or ""))
        if (
            not oof_path.is_file()
            or sha256(oof_path) != artifact.get("sha256")
        ):
            errors.append("OOF artifact identity mismatch")
    test_status = report.get("sealed_test_status")
    test_results = list(report.get("sealed_test_results") or [])
    if passed:
        if (
            report.get("status") != "VALIDATED_CANDIDATE"
            or test_status != "OPENED_ONCE_AFTER_VALIDATION_PASS"
            or report["sealed_test_artifact"].get("loaded") is not True
            or len(test_results) != len(passed)
        ):
            errors.append("passed validation did not produce one sealed evaluation")
    elif (
        report.get("status") != "RESEARCH_HOLD"
        or test_status != "SEALED_UNLOADED"
        or report["sealed_test_artifact"].get("loaded") is not False
        or test_results
    ):
        errors.append("failed validation did not preserve sealed test")
    allowed_test_keys = {
        (item["feature_set"], item["algorithm"]) for item in passed
    }
    if {
        (item.get("feature_set"), item.get("algorithm"))
        for item in test_results
    } != allowed_test_keys:
        errors.append("sealed results do not exactly match passed variants")
    for result in test_results:
        model_path = Path(str(result.get("model_artifact") or ""))
        if (
            not model_path.is_file()
            or sha256(model_path) != result.get("model_sha256")
        ):
            errors.append("model artifact identity mismatch")
    return {
        "status": "PASS" if not errors else "FAIL",
        "integrity_pass": not errors,
        "errors": errors,
        "model_id": MODEL_IDS[horizon],
        "horizon_sessions": horizon,
        "training_report": str(path.resolve()),
        "training_report_sha256": sha256(path),
        "validation_variants_passed": len(passed),
        "sealed_test_status": test_status,
        "research_only": True,
        "execution_decision": "AVOID",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h05-root", type=Path, required=True)
    parser.add_argument("--h20-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = {
        "5": audit_report(args.h05_root / "training_report.json", 5),
        "20": audit_report(args.h20_root / "training_report.json", 20),
    }
    result = {
        "status": (
            "PASS"
            if all(item["integrity_pass"] for item in results.values())
            else "FAIL"
        ),
        "integrity_pass": all(
            item["integrity_pass"] for item in results.values()
        ),
        "models": results,
        "research_only": True,
        "execution_decision": "AVOID",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2), flush=True)
    if not result["integrity_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
