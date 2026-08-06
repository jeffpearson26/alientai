from __future__ import annotations

"""Purged LightGBM/XGBoost screen for the pure technical-only panels."""

import argparse
import json
import pickle
from pathlib import Path

import pandas as pd

from alientai_v2.research.multiresolution_cross_sectional import (
    date_spearman,
    selection_metrics,
)
from train_multiresolution_cross_sectional import (
    ALGORITHMS,
    MIN_PANEL_DATES,
    evaluate_oof,
    feature_columns,
    make_model,
    matrix,
    sha256,
    split_dates,
)


FEATURE_SET = "daily_only"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, required=True)
    parser.add_argument("--horizon", type=int, choices=(5, 20), required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise ValueError(f"output root must be new or empty: {args.output_root}")
    args.output_root.mkdir(parents=True, exist_ok=True)

    manifest_path = args.panel_root / "manifest.json"
    audit_path = args.panel_root / "content_audit.json"
    panel_path = args.panel_root / "panel.csv.gz"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete" or audit.get("status") != "PASS":
        raise ValueError("panel and independent audit must both pass")
    expected_hash = manifest["artifacts"]["panel"]["sha256"]
    if sha256(panel_path) != expected_hash:
        raise ValueError("panel hash mismatch")
    if audit.get("panel_sha256") != expected_hash:
        raise ValueError("audit refers to a different panel hash")
    frame = pd.read_csv(panel_path)
    if len(frame) != int(manifest["rows"]):
        raise ValueError("panel row count mismatch")
    if frame.duplicated(["market_date", "symbol"]).any():
        raise ValueError("duplicate panel keys")
    panel_dates = int(frame["market_date"].nunique())
    minimum_dates = MIN_PANEL_DATES[args.horizon]
    if panel_dates < minimum_dates:
        raise ValueError(
            f"only {panel_dates} dates; {minimum_dates} are required"
        )

    split = split_dates(frame, args.horizon)
    development = frame[
        frame["market_date"].isin(split["development"])
    ].copy()
    reports = []
    any_passed = False
    for algorithm in ALGORITHMS:
        oof, report = evaluate_oof(
            development,
            algorithm=algorithm,
            feature_set=FEATURE_SET,
            horizon=args.horizon,
        )
        oof[
            [
                "market_date",
                "symbol",
                "model_score",
                f"label_{args.horizon}d_net_return_pct",
                f"label_{args.horizon}d_cross_sectional_rank",
            ]
        ].to_csv(
            args.output_root
            / f"technical_only_{algorithm}_oof_predictions.csv.gz",
            index=False,
            compression="gzip",
        )
        any_passed = any_passed or report["validation_passed"]
        reports.append(report)

    test_status = "SEALED_UNLOADED"
    test_reports = []
    if any_passed:
        test = frame[frame["market_date"].isin(split["sealed_test"])].copy()
        target = f"label_{args.horizon}d_cross_sectional_rank"
        return_column = f"label_{args.horizon}d_net_return_pct"
        for report in reports:
            if not report["validation_passed"]:
                continue
            columns = feature_columns(FEATURE_SET)
            model = make_model(report["algorithm"])
            model.fit(
                matrix(development, columns),
                development[target].astype(float),
            )
            test["model_score"] = model.predict(matrix(test, columns))
            threshold = report["selected_validation_policy"]["threshold"]
            metrics = selection_metrics(
                test,
                score_column="model_score",
                return_column=return_column,
                threshold=threshold,
            )
            mean_ic, ic_dates = date_spearman(
                test, "model_score", target
            )
            artifact = args.output_root / (
                f"technical_only_{report['algorithm']}_model.joblib"
            )
            with artifact.open("wb") as handle:
                pickle.dump(model, handle, protocol=pickle.HIGHEST_PROTOCOL)
            test_reports.append(
                {
                    "algorithm": report["algorithm"],
                    "threshold": threshold,
                    "metrics": metrics,
                    "mean_rank_ic": mean_ic,
                    "rank_ic_dates": ic_dates,
                    "model_artifact": str(artifact),
                    "model_sha256": sha256(artifact),
                }
            )
        test_status = "OPENED_ONCE_AFTER_VALIDATION_PASS"

    report = {
        "status": "VALIDATED_CANDIDATE" if any_passed else "RESEARCH_HOLD",
        "model_family": "technical_only_cross_sectional_ranker",
        "universe": manifest["universe"],
        "horizon_sessions": args.horizon,
        "panel": str(panel_path),
        "panel_sha256": expected_hash,
        "panel_rows": len(frame),
        "panel_dates": panel_dates,
        "split": {key: len(value) for key, value in split.items()},
        "split_dates": split,
        "sealed_test_rows": int(
            frame["market_date"].isin(split["sealed_test"]).sum()
        ),
        "sealed_test_status": test_status,
        "feature_set": FEATURE_SET,
        "feature_columns": feature_columns(FEATURE_SET),
        "explicitly_excluded": manifest["explicitly_excluded"],
        "variants": reports,
        "sealed_test_results": test_reports,
        "cost_pct": 0.25,
        "full_candidate_coverage_each_date": True,
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
                "status": report["status"],
                "universe": report["universe"],
                "horizon_sessions": args.horizon,
                "panel_dates": panel_dates,
                "development_dates": report["split"]["development"],
                "sealed_test_status": test_status,
                "report": str(report_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
