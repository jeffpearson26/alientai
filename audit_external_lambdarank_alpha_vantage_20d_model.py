from __future__ import annotations

"""Audit the Alpha Vantage LambdaRank model and its one-time sealed test."""

import argparse
import json
import math
from pathlib import Path

import lightgbm as lgb
import pandas as pd

from alientai_v2.research.external_lambdarank_alpha_vantage_20d import (
    FEATURE_COLUMNS,
    MINIMUM_CANDIDATES,
    MODEL_ID,
    score_metrics,
    sha256,
)
from train_external_lambdarank_20d import validation_gate


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def equivalent(left, right) -> bool:
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            equivalent(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            equivalent(a, b) for a, b in zip(left, right)
        )
    if (
        isinstance(left, (int, float))
        and not isinstance(left, bool)
        and isinstance(right, (int, float))
        and not isinstance(right, bool)
    ):
        return math.isclose(
            float(left), float(right), rel_tol=1e-12, abs_tol=1e-12
        )
    return left == right


def _audit_predictions(
    artifact: dict, expected_metrics: dict
) -> tuple[pd.DataFrame, dict]:
    path = Path(artifact["path"])
    require(sha256(path) == artifact["sha256"], "prediction hash mismatch")
    frame = pd.read_csv(path)
    require(
        not frame.duplicated(["market_date", "symbol"]).any(),
        "prediction keys are duplicated",
    )
    require(
        frame.groupby("market_date")["symbol"]
        .nunique()
        .eq(MINIMUM_CANDIDATES)
        .all(),
        "prediction dates are incomplete",
    )
    metrics = score_metrics(frame)
    require(
        equivalent(metrics, expected_metrics),
        "reported metrics are not reproducible",
    )
    return frame, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    panel_audit_path = (
        args.panel_root / "independent_content_audit.json"
    )
    training_path = args.model_root / "training_report.json"
    metadata_path = args.model_root / "model_metadata.json"
    model_path = args.model_root / "model.txt"
    panel_audit = json.loads(panel_audit_path.read_text(encoding="utf-8"))
    training = json.loads(training_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    require(panel_audit["status"] == "PASS", "panel audit did not pass")
    require(
        panel_audit["model_id"] == MODEL_ID,
        "panel audit model ID mismatch",
    )
    require(
        training["status"] == "READY_FOR_FUTURE_ONLY_TEST",
        "training is not ready",
    )
    require(
        training["model_id"] == MODEL_ID
        and metadata["model_id"] == MODEL_ID,
        "model ID mismatch",
    )
    require(
        training["sealed_test_status"] == "OPENED_ONCE_PASS",
        "sealed test status mismatch",
    )
    require(
        metadata["sealed_test_status"] == "OPENED_ONCE_PASS",
        "metadata sealed status mismatch",
    )
    require(
        sha256(model_path) == metadata["model_sha256"],
        "model hash mismatch",
    )
    require(
        sha256(metadata_path)
        == training["model_artifact"]["metadata_sha256"],
        "metadata hash mismatch",
    )
    require(
        metadata["feature_columns"] == list(FEATURE_COLUMNS),
        "feature order mismatch",
    )
    booster = lgb.Booster(model_file=str(model_path))
    require(
        booster.feature_name() == list(FEATURE_COLUMNS),
        "LightGBM feature names mismatch",
    )

    development, development_metrics = _audit_predictions(
        training["development_oof_predictions"],
        training["development_metrics"],
    )
    sealed, sealed_metrics = _audit_predictions(
        training["sealed_test_predictions"],
        training["sealed_test_metrics"],
    )
    require(
        set(development["market_date"]).isdisjoint(
            set(sealed["market_date"])
        ),
        "development and sealed dates overlap",
    )
    development_gate = validation_gate(development_metrics)
    sealed_gate = validation_gate(sealed_metrics)
    require(
        development_gate == training["development_gate"]
        and development_gate["passed"],
        "development gate is not reproducible",
    )
    require(
        sealed_gate == training["sealed_test_gate"]
        and sealed_gate["passed"],
        "sealed-test gate is not reproducible",
    )
    require(
        metadata["prospective_eligible_after_session"]
        > metadata["last_training_date"],
        "prospective cutoff does not follow training decisions",
    )
    require(
        metadata["prospective_eligible_after_session"]
        >= metadata["last_training_label_exit_date"],
        "prospective cutoff precedes a training outcome",
    )
    require(
        metadata["future_test_status"] == "NOT_STARTED"
        and training["future_test_status"] == "NOT_STARTED",
        "future test is not unopened",
    )

    report = {
        "status": "PASS",
        "model_id": MODEL_ID,
        "model_sha256": sha256(model_path),
        "training_report_sha256": sha256(training_path),
        "metadata_sha256": sha256(metadata_path),
        "panel_audit_sha256": sha256(panel_audit_path),
        "development_rows": len(development),
        "development_dates": int(
            development["market_date"].nunique()
        ),
        "sealed_rows": len(sealed),
        "sealed_dates": int(sealed["market_date"].nunique()),
        "development_gate": development_gate,
        "sealed_test_gate": sealed_gate,
        "sealed_test_status": "OPENED_ONCE_PASS",
        "prospective_eligible_after_session": metadata[
            "prospective_eligible_after_session"
        ],
        "future_test_status": "NOT_STARTED",
        "serialization": "LightGBM text model",
        "source_provider": "Alpha Vantage",
        "research_only": True,
        "execution_decision": "AVOID",
    }
    output = args.report or (
        args.model_root / "independent_model_audit.json"
    )
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
