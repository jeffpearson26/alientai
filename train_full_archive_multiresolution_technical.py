from __future__ import annotations

"""Train one frozen full-archive technical horizon without premature test use."""

import argparse
import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd

from alientai_v2.research.multiresolution_cross_sectional import (
    date_spearman,
    selection_metrics,
)
from build_full_archive_multiresolution_technical_panel import MODEL_FAMILY, sha256
from train_multiresolution_cross_sectional import (
    ALGORITHMS,
    evaluate_oof,
    make_model,
    matrix,
)


FEATURE_SETS = ("daily_only", "daily_plus_5minute")
MODEL_IDS = {
    5: "full_archive_multiresolution_nasdaq101_h05_v1_20260807",
    20: "full_archive_multiresolution_nasdaq101_h20_v1_20260807",
}


def verified_frame(artifact: dict[str, Any]) -> pd.DataFrame:
    path = Path(str(artifact["path"]))
    if sha256(path) != artifact["sha256"]:
        raise ValueError(f"artifact hash mismatch: {path}")
    frame = pd.read_csv(path)
    if (
        len(frame) != int(artifact["rows"])
        or frame["market_date"].nunique() != int(artifact["dates"])
        or frame.duplicated(["market_date", "symbol"]).any()
    ):
        raise ValueError(f"artifact row/date/key mismatch: {path}")
    return frame


def run(panel_root: Path, horizon: int, output_root: Path) -> dict[str, Any]:
    if output_root.exists() and any(output_root.iterdir()):
        raise ValueError(f"output root must be new or empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = panel_root / "manifest.json"
    audit_path = panel_root / "content_audit.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "complete"
        or manifest.get("model_family") != MODEL_FAMILY
        or not audit.get("integrity_pass")
        or audit.get("manifest_sha256") != sha256(manifest_path)
    ):
        raise ValueError("panel manifest/content audit is not eligible")
    partition = manifest["artifacts"]["partitions"][str(horizon)]
    # The development artifact is the only outcome-bearing shard loaded before
    # the validation gate. The sealed-test artifact is not read here.
    development = verified_frame(partition["development"])
    target = f"label_{horizon}d_cross_sectional_rank"
    return_column = f"label_{horizon}d_net_return_pct"
    variants: list[dict[str, Any]] = []
    any_passed = False
    for feature_set in FEATURE_SETS:
        for algorithm in ALGORITHMS:
            oof, report = evaluate_oof(
                development,
                algorithm=algorithm,
                feature_set=feature_set,
                horizon=horizon,
            )
            oof_path = (
                output_root / f"{feature_set}_{algorithm}_oof_predictions.csv.gz"
            )
            oof[
                [
                    "market_date",
                    "symbol",
                    "model_score",
                    return_column,
                    target,
                ]
            ].to_csv(
                oof_path,
                index=False,
                compression="gzip",
            )
            report["oof_artifact"] = {
                "path": str(oof_path.resolve()),
                "sha256": sha256(oof_path),
                "rows": len(oof),
                "dates": int(oof["market_date"].nunique()),
            }
            variants.append(report)
            any_passed = any_passed or bool(report["validation_passed"])
    sealed_test_status = "SEALED_UNLOADED"
    sealed_test_results: list[dict[str, Any]] = []
    if any_passed:
        # This is the only permitted first read of the independently hashed
        # sealed-test shard, and it occurs only after all validation decisions.
        test = verified_frame(partition["sealed_test"])
        for report in variants:
            if not report["validation_passed"]:
                continue
            columns = report["feature_columns"]
            model = make_model(report["algorithm"])
            model.fit(
                matrix(development, columns),
                development[target].astype(float),
            )
            candidate_test = test.copy()
            candidate_test["model_score"] = model.predict(
                matrix(candidate_test, columns)
            )
            threshold = report["selected_validation_policy"]["threshold"]
            metrics = selection_metrics(
                candidate_test,
                score_column="model_score",
                return_column=return_column,
                threshold=threshold,
            )
            mean_ic, ic_dates = date_spearman(
                candidate_test,
                "model_score",
                target,
            )
            model_path = (
                output_root
                / f"{report['feature_set']}_{report['algorithm']}_model.joblib"
            )
            with model_path.open("wb") as handle:
                pickle.dump(model, handle, protocol=pickle.HIGHEST_PROTOCOL)
            sealed_test_results.append(
                {
                    "algorithm": report["algorithm"],
                    "feature_set": report["feature_set"],
                    "threshold": threshold,
                    "metrics": metrics,
                    "mean_rank_ic": mean_ic,
                    "rank_ic_dates": ic_dates,
                    "model_artifact": str(model_path.resolve()),
                    "model_sha256": sha256(model_path),
                }
            )
        sealed_test_status = "OPENED_ONCE_AFTER_VALIDATION_PASS"
    result = {
        "status": "VALIDATED_CANDIDATE" if any_passed else "RESEARCH_HOLD",
        "model_id": MODEL_IDS[horizon],
        "model_family": MODEL_FAMILY,
        "horizon_sessions": horizon,
        "feature_sets": list(FEATURE_SETS),
        "algorithms": list(ALGORITHMS),
        "panel_manifest_path": str(manifest_path.resolve()),
        "panel_manifest_sha256": sha256(manifest_path),
        "panel_audit_path": str(audit_path.resolve()),
        "panel_audit_sha256": sha256(audit_path),
        "development_artifact": partition["development"],
        "pre_test_embargo_dates": len(
            partition["split_dates"]["pre_test_embargo"]
        ),
        "sealed_test_artifact": {
            **partition["sealed_test"],
            "loaded": any_passed,
        },
        "sealed_test_status": sealed_test_status,
        "variants": variants,
        "sealed_test_results": sealed_test_results,
        "cost_pct": 0.25,
        "fixed_current_universe_survivorship_bias": True,
        "research_only": True,
        "execution_decision": "AVOID",
    }
    report_path = output_root / "training_report.json"
    report_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "model_id": result["model_id"],
                "horizon_sessions": horizon,
                "development_dates": development["market_date"].nunique(),
                "validation_variants_passed": sum(
                    item["validation_passed"] for item in variants
                ),
                "sealed_test_status": sealed_test_status,
                "report": str(report_path.resolve()),
            },
            indent=2,
        ),
        flush=True,
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, required=True)
    parser.add_argument("--horizon", type=int, choices=(5, 20), required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    run(args.panel_root, args.horizon, args.output_root)


if __name__ == "__main__":
    main()
