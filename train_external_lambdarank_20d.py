from __future__ import annotations

"""Run development-only purged CV for the corrected external LambdaRank lead."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import lightgbm as lgb
import numpy as np
import pandas as pd

from alientai_v2.research.external_lambdarank_20d import (
    FEATURE_COLUMNS,
    HORIZON_SESSIONS,
    MODEL_ID,
    purged_folds,
    score_metrics,
    sha256,
)


MODEL_PARAMETERS = {
    "objective": "lambdarank",
    "learning_rate": 0.05,
    "max_depth": 6,
    "num_leaves": 31,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "feature_fraction": 0.8,
    "lambda_l2": 1.0,
    "seed": 42,
    "verbosity": -1,
    "num_threads": 0,
}
NUM_BOOST_ROUND = 300


def fit_ranker(frame: pd.DataFrame) -> lgb.Booster:
    ordered = frame.sort_values(["market_date", "symbol"]).copy()
    groups = ordered.groupby("market_date", sort=True).size().to_numpy()
    if len(groups) == 0 or int(groups.min()) != int(groups.max()):
        raise ValueError("LambdaRank requires complete equal-size date groups")
    training = lgb.Dataset(
        ordered[list(FEATURE_COLUMNS)],
        label=ordered["relevance"].astype(int),
        group=groups,
        feature_name=list(FEATURE_COLUMNS),
        free_raw_data=False,
    )
    return lgb.train(
        MODEL_PARAMETERS,
        training,
        num_boost_round=NUM_BOOST_ROUND,
    )


def validation_gate(metrics: dict[str, Any]) -> dict[str, Any]:
    rotations = [
        item["compounded_return_pct"]
        for item in metrics["nonoverlap_rotations"]
        if item["compounded_return_pct"] is not None
    ]
    checks = {
        "rank_ic_at_least_0_02": (
            metrics["mean_rank_ic"] is not None
            and metrics["mean_rank_ic"] >= 0.02
        ),
        "positive_selected10_mean_net": (
            metrics["selected10_mean_net_return_pct"] is not None
            and metrics["selected10_mean_net_return_pct"] > 0.0
        ),
        "selected10_median_not_materially_negative": (
            metrics["selected10_median_net_return_pct"] is not None
            and metrics["selected10_median_net_return_pct"] >= -0.25
        ),
        "positive_top_minus_bottom": (
            metrics["top_minus_bottom_mean_pct"] is not None
            and metrics["top_minus_bottom_mean_pct"] > 0.0
        ),
        "minimum_100_validation_dates": metrics["rank_ic_dates"] >= 100,
        "majority_positive_nonoverlap_rotations": (
            len(rotations) >= 10
            and sum(value > 0.0 for value in rotations) / len(rotations)
            >= 0.60
        ),
    }
    return {"passed": all(checks.values()), "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    frozen_at_utc = datetime.now(timezone.utc).isoformat()
    prospective_eligible_after_session = datetime.now(
        ZoneInfo("America/Los_Angeles")
    ).date().isoformat()
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise ValueError(f"output root must be new or empty: {args.output_root}")
    manifest_path = args.panel_root / "manifest.json"
    panel_path = args.panel_root / "labeled_panel.csv.gz"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "complete"
        or manifest.get("model_id") != MODEL_ID
    ):
        raise ValueError("panel manifest is not the corrected LambdaRank panel")
    expected_hash = manifest["artifacts"]["labeled_panel"]["sha256"]
    if sha256(panel_path) != expected_hash:
        raise ValueError("labeled panel hash mismatch")
    frame = pd.read_csv(panel_path)
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
    if not required.issubset(frame.columns):
        raise ValueError(f"panel missing {sorted(required - set(frame))}")
    if len(frame) != int(manifest["artifacts"]["labeled_panel"]["rows"]):
        raise ValueError("panel row count mismatch")
    if frame.duplicated(["market_date", "symbol"]).any():
        raise ValueError("duplicate panel keys")
    if frame[list(FEATURE_COLUMNS)].isna().any().any():
        raise ValueError("model features contain missing values")

    predictions = []
    fold_reports = []
    for fold in purged_folds(frame, n_splits=5):
        train = frame[frame["market_date"].isin(fold.train_dates)].copy()
        validation = frame[
            frame["market_date"].isin(fold.validation_dates)
        ].copy()
        if train["market_date"].nunique() < 60:
            raise ValueError(f"fold {fold.fold} has insufficient train dates")
        model = fit_ranker(train)
        ordered = validation.sort_values(["market_date", "symbol"]).copy()
        ordered["model_score"] = model.predict(
            ordered[list(FEATURE_COLUMNS)]
        )
        predictions.append(ordered)
        fold_reports.append(
            {
                "fold": fold.fold,
                "train_dates": len(fold.train_dates),
                "validation_dates": len(fold.validation_dates),
                "purged_dates": len(fold.purged_dates),
                "embargo_dates": len(fold.embargo_dates),
                "train_rows": len(train),
                "validation_rows": len(validation),
                "metrics": score_metrics(ordered),
            }
        )
    oof = pd.concat(predictions, ignore_index=True)
    if oof.duplicated(["market_date", "symbol"]).any():
        raise ValueError("duplicate out-of-fold predictions")
    overall = score_metrics(oof)
    gate = validation_gate(overall)
    status = (
        "READY_FOR_FUTURE_ONLY_TEST"
        if gate["passed"]
        else "RESEARCH_HOLD_DEVELOPMENT_GATE_FAILED"
    )

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

    model_artifact = None
    model_metadata = None
    if gate["passed"]:
        final_model = fit_ranker(frame)
        model_path = args.output_root / "model.txt"
        final_model.save_model(str(model_path))
        model_metadata = {
            "model_id": MODEL_ID,
            "model_path": str(model_path.resolve()),
            "model_sha256": sha256(model_path),
            "feature_columns": list(FEATURE_COLUMNS),
            "parameters": {
                **MODEL_PARAMETERS,
                "num_boost_round": NUM_BOOST_ROUND,
            },
            "training_rows": len(frame),
            "training_dates": int(frame["market_date"].nunique()),
            "first_training_date": str(frame["market_date"].min()),
            "last_training_date": str(frame["market_date"].max()),
            "last_training_label_exit_date": str(
                frame["label_exit_date"].max()
            ),
            "frozen_at_utc": frozen_at_utc,
            "prospective_eligible_after_session": (
                prospective_eligible_after_session
            ),
            "panel_sha256": expected_hash,
            "manifest_sha256": sha256(manifest_path),
            "future_test_status": "NOT_STARTED",
            "research_only": True,
            "execution_decision": "AVOID",
        }
        metadata_path = args.output_root / "model_metadata.json"
        metadata_path.write_text(
            json.dumps(model_metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        model_artifact = {
            "path": str(model_path.resolve()),
            "sha256": model_metadata["model_sha256"],
            "metadata_path": str(metadata_path.resolve()),
            "metadata_sha256": sha256(metadata_path),
        }

    report = {
        "status": status,
        "model_id": MODEL_ID,
        "model_family": "LightGBM LambdaRank cross-sectional ranker",
        "horizon_sessions": HORIZON_SESSIONS,
        "source_manifest": str(manifest_path.resolve()),
        "source_manifest_sha256": sha256(manifest_path),
        "panel": str(panel_path.resolve()),
        "panel_sha256": expected_hash,
        "rows": len(frame),
        "dates": int(frame["market_date"].nunique()),
        "features": list(FEATURE_COLUMNS),
        "parameters": {
            **MODEL_PARAMETERS,
            "num_boost_round": NUM_BOOST_ROUND,
        },
        "folds": fold_reports,
        "development_metrics": overall,
        "development_gate": gate,
        "oof_predictions": {
            "path": str(oof_path.resolve()),
            "sha256": sha256(oof_path),
        },
        "model_artifact": model_artifact,
        "external_claimed_holdout": (
            "EXPOSED_AND_NOT_USED_AS_A_SEALED_TEST"
        ),
        "frozen_at_utc": frozen_at_utc,
        "prospective_eligible_after_session": (
            prospective_eligible_after_session
        ),
        "sealed_test_status": (
            "FUTURE_ONLY_NOT_STARTED"
            if gate["passed"]
            else "NOT_STARTED_DEVELOPMENT_GATE_FAILED"
        ),
        "fixed_current_universe_survivorship_bias": True,
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
                "rows": len(frame),
                "dates": int(frame["market_date"].nunique()),
                "development_metrics": overall,
                "gate": gate,
                "sealed_test_status": report["sealed_test_status"],
                "report": str(report_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
