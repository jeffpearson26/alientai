from __future__ import annotations

"""Audit the safe model artifact and development-only OOF evidence."""

import argparse
import json
import math
from pathlib import Path

import lightgbm as lgb
import pandas as pd

from alientai_v2.research.external_lambdarank_20d import (
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    panel_audit_path = (
        args.panel_root / "independent_content_audit.json"
    )
    training_report_path = args.model_root / "training_report.json"
    metadata_path = args.model_root / "model_metadata.json"
    model_path = args.model_root / "model.txt"
    panel_audit = json.loads(panel_audit_path.read_text(encoding="utf-8"))
    training = json.loads(
        training_report_path.read_text(encoding="utf-8")
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    require(panel_audit["status"] == "PASS", "panel audit did not pass")
    require(
        training["status"] == "READY_FOR_FUTURE_ONLY_TEST",
        "development gate did not pass",
    )
    require(training["model_id"] == MODEL_ID, "training model ID mismatch")
    require(metadata["model_id"] == MODEL_ID, "metadata model ID mismatch")
    require(
        metadata["feature_columns"] == list(FEATURE_COLUMNS),
        "metadata feature contract mismatch",
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
    oof_path = Path(training["oof_predictions"]["path"])
    require(
        sha256(oof_path) == training["oof_predictions"]["sha256"],
        "OOF prediction hash mismatch",
    )

    booster = lgb.Booster(model_file=str(model_path))
    require(
        booster.feature_name() == list(FEATURE_COLUMNS),
        "LightGBM feature order mismatch",
    )
    oof = pd.read_csv(oof_path)
    require(
        not oof.duplicated(["market_date", "symbol"]).any(),
        "OOF predictions have duplicate keys",
    )
    require(
        oof.groupby("market_date")["symbol"].nunique().eq(
            MINIMUM_CANDIDATES
        ).all(),
        "OOF predictions have incomplete dates",
    )
    recomputed = score_metrics(oof)
    require(
        equivalent(recomputed, training["development_metrics"]),
        "development metrics are not reproducible within numeric tolerance",
    )
    gate = validation_gate(recomputed)
    require(gate == training["development_gate"], "gate is not reproducible")
    require(gate["passed"], "recomputed gate failed")
    require(
        metadata["prospective_eligible_after_session"]
        > metadata["last_training_date"],
        "prospective cutoff does not follow training data",
    )
    require(
        metadata["future_test_status"] == "NOT_STARTED",
        "future test has already been opened",
    )

    report = {
        "status": "PASS",
        "model_id": MODEL_ID,
        "model_sha256": sha256(model_path),
        "training_report_sha256": sha256(training_report_path),
        "metadata_sha256": sha256(metadata_path),
        "oof_sha256": sha256(oof_path),
        "development_dates": int(oof["market_date"].nunique()),
        "development_rows": len(oof),
        "development_gate": gate,
        "prospective_eligible_after_session": metadata[
            "prospective_eligible_after_session"
        ],
        "future_test_status": "NOT_STARTED",
        "bundled_joblib": "QUARANTINED_NEVER_LOADED",
        "serialization": "LightGBM text model",
        "research_only": True,
        "execution_decision": "AVOID",
    }
    report_path = args.report or (
        args.model_root / "independent_model_audit.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
