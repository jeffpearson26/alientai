from __future__ import annotations

"""Train the isolated Alpha Vantage LambdaRank clone with a sealed test."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from alientai_v2.research.external_lambdarank_alpha_vantage_20d import (
    FEATURE_COLUMNS,
    HORIZON_SESSIONS,
    MODEL_ID,
    purged_folds,
    score_metrics,
    sha256,
)
from train_external_lambdarank_20d import (
    MODEL_PARAMETERS,
    NUM_BOOST_ROUND,
    fit_ranker,
    validation_gate,
)


def _validate_panel(
    frame: pd.DataFrame, expected_rows: int
) -> None:
    required = {
        "market_date",
        "symbol",
        "label_entry_date",
        "label_exit_date",
        "label_net_return_pct",
        "target_return_rank",
        "relevance",
        *FEATURE_COLUMNS,
    }
    if len(frame) != expected_rows:
        raise ValueError("panel row count mismatch")
    if not required.issubset(frame):
        raise ValueError(f"panel missing {sorted(required - set(frame))}")
    if frame.duplicated(["market_date", "symbol"]).any():
        raise ValueError("panel has duplicate keys")
    if frame[list(FEATURE_COLUMNS)].isna().any().any():
        raise ValueError("panel has missing model features")


def _score(model, frame: pd.DataFrame) -> pd.DataFrame:
    ordered = frame.sort_values(["market_date", "symbol"]).copy()
    ordered["model_score"] = model.predict(
        ordered[list(FEATURE_COLUMNS)]
    )
    return ordered


def development_oof(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    predictions = []
    reports = []
    for fold in purged_folds(frame, n_splits=5):
        train = frame[frame["market_date"].isin(fold.train_dates)].copy()
        validation = frame[
            frame["market_date"].isin(fold.validation_dates)
        ].copy()
        if train["market_date"].nunique() < 60:
            raise ValueError(f"fold {fold.fold} has insufficient dates")
        scored = _score(fit_ranker(train), validation)
        predictions.append(scored)
        reports.append(
            {
                "fold": fold.fold,
                "train_dates": len(fold.train_dates),
                "validation_dates": len(fold.validation_dates),
                "purged_dates": len(fold.purged_dates),
                "embargo_dates": len(fold.embargo_dates),
                "train_rows": len(train),
                "validation_rows": len(validation),
                "metrics": score_metrics(scored),
            }
        )
    oof = pd.concat(predictions, ignore_index=True)
    if oof.duplicated(["market_date", "symbol"]).any():
        raise ValueError("OOF predictions have duplicate keys")
    return oof, reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise ValueError(f"output root must be new or empty: {args.output_root}")
    manifest_path = args.panel_root / "manifest.json"
    audit_path = args.panel_root / "independent_content_audit.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "complete"
        or manifest.get("model_id") != MODEL_ID
        or audit.get("status") != "PASS"
        or audit.get("model_id") != MODEL_ID
    ):
        raise ValueError("panel or independent audit is not valid")

    development_artifact = manifest["artifacts"]["development_panel"]
    development_path = Path(development_artifact["path"])
    if sha256(development_path) != development_artifact["sha256"]:
        raise ValueError("development panel hash mismatch")
    development = pd.read_csv(development_path)
    _validate_panel(development, int(development_artifact["rows"]))

    oof, folds = development_oof(development)
    development_metrics = score_metrics(oof)
    development_gate = validation_gate(development_metrics)
    args.output_root.mkdir(parents=True, exist_ok=True)
    oof_path = args.output_root / "development_oof_predictions.csv.gz"
    oof[
        [
            "market_date",
            "symbol",
            "model_score",
            "target_return_rank",
            "label_net_return_pct",
        ]
    ].to_csv(oof_path, index=False, compression="gzip")

    sealed_status = "SEALED_UNLOADED_DEVELOPMENT_GATE_FAILED"
    sealed_metrics = None
    sealed_gate = None
    sealed_predictions = None
    if development_gate["passed"]:
        sealed_artifact = manifest["artifacts"]["sealed_test_panel"]
        sealed_path = Path(sealed_artifact["path"])
        if sha256(sealed_path) != sealed_artifact["sha256"]:
            raise ValueError("sealed panel hash mismatch")
        sealed = pd.read_csv(sealed_path)
        _validate_panel(sealed, int(sealed_artifact["rows"]))
        sealed_scored = _score(fit_ranker(development), sealed)
        sealed_metrics = score_metrics(sealed_scored)
        sealed_gate = validation_gate(sealed_metrics)
        sealed_predictions_path = (
            args.output_root / "sealed_test_predictions.csv.gz"
        )
        sealed_scored[
            [
                "market_date",
                "symbol",
                "model_score",
                "target_return_rank",
                "label_net_return_pct",
            ]
        ].to_csv(
            sealed_predictions_path, index=False, compression="gzip"
        )
        sealed_predictions = {
            "path": str(sealed_predictions_path.resolve()),
            "sha256": sha256(sealed_predictions_path),
        }
        sealed_status = (
            "OPENED_ONCE_PASS"
            if sealed_gate["passed"]
            else "OPENED_ONCE_FAIL"
        )

    model_artifact = None
    if development_gate["passed"] and sealed_gate and sealed_gate["passed"]:
        full_artifact = manifest["artifacts"]["labeled_panel"]
        full_path = Path(full_artifact["path"])
        if sha256(full_path) != full_artifact["sha256"]:
            raise ValueError("full labeled panel hash mismatch")
        full = pd.read_csv(full_path)
        _validate_panel(full, int(full_artifact["rows"]))
        final_model = fit_ranker(full)
        model_path = args.output_root / "model.txt"
        final_model.save_model(str(model_path))
        metadata = {
            "model_id": MODEL_ID,
            "model_path": str(model_path.resolve()),
            "model_sha256": sha256(model_path),
            "feature_columns": list(FEATURE_COLUMNS),
            "parameters": {
                **MODEL_PARAMETERS,
                "num_boost_round": NUM_BOOST_ROUND,
            },
            "training_rows": len(full),
            "training_dates": int(full["market_date"].nunique()),
            "first_training_date": str(full["market_date"].min()),
            "last_training_date": str(full["market_date"].max()),
            "last_training_label_exit_date": str(
                full["label_exit_date"].max()
            ),
            "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
            "prospective_eligible_after_session": manifest[
                "source_contract"
            ]["as_of_session"],
            "panel_sha256": full_artifact["sha256"],
            "manifest_sha256": sha256(manifest_path),
            "sealed_test_status": sealed_status,
            "future_test_status": "NOT_STARTED",
            "source_provider": "Alpha Vantage",
            "research_only": True,
            "execution_decision": "AVOID",
        }
        metadata_path = args.output_root / "model_metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        model_artifact = {
            "path": str(model_path.resolve()),
            "sha256": metadata["model_sha256"],
            "metadata_path": str(metadata_path.resolve()),
            "metadata_sha256": sha256(metadata_path),
        }

    if not development_gate["passed"]:
        status = "RESEARCH_HOLD_DEVELOPMENT_GATE_FAILED"
    elif not sealed_gate or not sealed_gate["passed"]:
        status = "RESEARCH_HOLD_SEALED_TEST_FAILED"
    else:
        status = "READY_FOR_FUTURE_ONLY_TEST"
    report = {
        "status": status,
        "model_id": MODEL_ID,
        "model_family": "LightGBM LambdaRank cross-sectional ranker",
        "source_provider": "Alpha Vantage",
        "horizon_sessions": HORIZON_SESSIONS,
        "panel_manifest": str(manifest_path.resolve()),
        "panel_manifest_sha256": sha256(manifest_path),
        "panel_audit_sha256": sha256(audit_path),
        "parameters": {
            **MODEL_PARAMETERS,
            "num_boost_round": NUM_BOOST_ROUND,
        },
        "development_rows": len(development),
        "development_dates": int(
            development["market_date"].nunique()
        ),
        "development_folds": folds,
        "development_metrics": development_metrics,
        "development_gate": development_gate,
        "development_oof_predictions": {
            "path": str(oof_path.resolve()),
            "sha256": sha256(oof_path),
        },
        "sealed_test_status": sealed_status,
        "sealed_test_metrics": sealed_metrics,
        "sealed_test_gate": sealed_gate,
        "sealed_test_predictions": sealed_predictions,
        "model_artifact": model_artifact,
        "prospective_eligible_after_session": manifest[
            "source_contract"
        ]["as_of_session"],
        "future_test_status": "NOT_STARTED",
        "fixed_current_universe_survivorship_bias": True,
        "historical_adjustment_revision_risk": True,
        "research_only": True,
        "execution_decision": "AVOID",
    }
    report_path = args.output_root / "training_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": status,
                "development_metrics": development_metrics,
                "development_gate": development_gate,
                "sealed_test_status": sealed_status,
                "sealed_test_metrics": sealed_metrics,
                "sealed_test_gate": sealed_gate,
                "model_artifact": model_artifact,
                "report": str(report_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
