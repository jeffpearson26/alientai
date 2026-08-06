from __future__ import annotations

"""Purged historical screening for the daily-only cross-sectional ranker."""

import argparse
import json
import pickle
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from alientai_v2.research.multiresolution_cross_sectional import (
    CONTEXT_FEATURES,
    DAILY_FEATURES,
    OPTION_FEATURES,
    date_spearman,
    purged_date_folds,
    selection_metrics,
)
from train_multiresolution_cross_sectional import (
    ALGORITHMS,
    MIN_PANEL_DATES,
    POLICY_THRESHOLDS,
    make_model,
    matrix,
    sha256,
    split_dates,
    validation_gate,
)


FEATURE_SETS = {
    "daily_technical": DAILY_FEATURES + CONTEXT_FEATURES,
    "daily_technical_options": DAILY_FEATURES
    + OPTION_FEATURES
    + ("option_available",)
    + CONTEXT_FEATURES,
}


def feature_columns(feature_set: str) -> list[str]:
    output = []
    for name in FEATURE_SETS[feature_set]:
        if name in CONTEXT_FEATURES or name == "option_available":
            output.append(name)
        else:
            output.append(f"rank_{name}")
    return output


def evaluate_oof(
    development: pd.DataFrame,
    *,
    algorithm: str,
    feature_set: str,
    horizon: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    target = f"label_{horizon}d_cross_sectional_rank"
    return_column = f"label_{horizon}d_net_return_pct"
    columns = feature_columns(feature_set)
    folds = purged_date_folds(
        development[
            [
                "market_date",
                f"label_{horizon}d_entry_date",
                f"label_{horizon}d_exit_date",
            ]
        ].rename(
            columns={
                f"label_{horizon}d_entry_date": "label_entry_date",
                f"label_{horizon}d_exit_date": "label_exit_date",
            }
        ),
        horizon_sessions=horizon,
        n_splits=3,
    )
    predictions = []
    fold_reports = []
    for fold in folds:
        train = development[development["market_date"].isin(fold.train_dates)]
        validation = development[
            development["market_date"].isin(fold.validation_dates)
        ].copy()
        if (
            len(train) < 500
            or train["market_date"].nunique() < 10
            or validation.empty
        ):
            raise ValueError(f"insufficient rows in fold {fold.fold}")
        model = make_model(algorithm)
        model.fit(matrix(train, columns), train[target].astype(float))
        validation["model_score"] = model.predict(matrix(validation, columns))
        predictions.append(validation)
        fold_ic, fold_ic_dates = date_spearman(
            validation, "model_score", target
        )
        fold_reports.append(
            {
                "fold": fold.fold,
                "train_dates": len(fold.train_dates),
                "validation_dates": len(fold.validation_dates),
                "purged_dates": list(fold.purged_dates),
                "embargo_dates": list(fold.embargo_dates),
                "train_rows": len(train),
                "validation_rows": len(validation),
                "mean_rank_ic": fold_ic,
                "rank_ic_dates": fold_ic_dates,
            }
        )
    oof = pd.concat(predictions, ignore_index=True)
    if oof.duplicated(["market_date", "symbol"]).any():
        raise ValueError("duplicate out-of-fold prediction")
    mean_ic, ic_dates = date_spearman(oof, "model_score", target)
    policies = []
    for threshold in POLICY_THRESHOLDS:
        metrics = selection_metrics(
            oof,
            score_column="model_score",
            return_column=return_column,
            threshold=threshold,
        )
        policies.append(
            {
                "threshold": threshold,
                "metrics": metrics,
                "gate": validation_gate(metrics, mean_ic),
            }
        )
    selected = max(
        policies,
        key=lambda item: (
            bool(item["gate"]["passed"]),
            item["metrics"]["mean_net_return_pct"]
            if item["metrics"]["mean_net_return_pct"] is not None
            else -np.inf,
            item["threshold"],
        ),
    )
    report = {
        "algorithm": algorithm,
        "feature_set": feature_set,
        "feature_columns": columns,
        "horizon_sessions": horizon,
        "development_rows": len(development),
        "development_dates": int(development["market_date"].nunique()),
        "mean_rank_ic": mean_ic,
        "rank_ic_dates": ic_dates,
        "folds": fold_reports,
        "policies": policies,
        "selected_validation_policy": selected,
        "validation_passed": bool(selected["gate"]["passed"]),
    }
    return oof, report


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
    panel_path = args.panel_root / "panel.csv.gz"
    audit_path = args.panel_root / "content_audit.json"
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
    universe = str(manifest["universe"])
    panel_dates = int(frame["market_date"].nunique())
    minimum_dates = MIN_PANEL_DATES[args.horizon]
    if panel_dates < minimum_dates:
        blocker = (
            f"only {panel_dates} common point-in-time dates are available; "
            f"{minimum_dates} are required for the {args.horizon}-session "
            "purge, embargo, and sealed-test geometry"
        )
        report = {
            "status": "BLOCKED_INSUFFICIENT_HISTORY",
            "model_family": "daily_options_cross_sectional_ranker",
            "universe": universe,
            "horizon_sessions": args.horizon,
            "panel": str(panel_path),
            "panel_sha256": expected_hash,
            "panel_rows": len(frame),
            "panel_dates": panel_dates,
            "minimum_required_dates": minimum_dates,
            "exact_blocker": blocker,
            "variants": [],
            "sealed_test_status": "NOT_CREATED_INSUFFICIENT_CHRONOLOGY",
            "research_only": True,
            "execution_decision": "AVOID",
        }
        report_path = args.output_root / "training_report.json"
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, indent=2))
        return

    split = split_dates(frame, args.horizon)
    development = frame[
        frame["market_date"].isin(split["development"])
    ].copy()
    sealed_test_rows = int(
        frame["market_date"].isin(split["sealed_test"]).sum()
    )
    variant_reports = []
    any_passed = False
    for feature_set in FEATURE_SETS:
        columns = feature_columns(feature_set)
        missing = [column for column in columns if column not in development]
        if missing:
            raise ValueError(f"{feature_set} missing columns: {missing}")
        for algorithm in ALGORITHMS:
            oof, report = evaluate_oof(
                development,
                algorithm=algorithm,
                feature_set=feature_set,
                horizon=args.horizon,
            )
            stem = f"{feature_set}_{algorithm}"
            oof[
                [
                    "market_date",
                    "symbol",
                    "model_score",
                    f"label_{args.horizon}d_net_return_pct",
                    f"label_{args.horizon}d_cross_sectional_rank",
                ]
            ].to_csv(
                args.output_root / f"{stem}_oof_predictions.csv.gz",
                index=False,
                compression="gzip",
            )
            any_passed = any_passed or report["validation_passed"]
            variant_reports.append(report)

    test_status = "SEALED_UNLOADED"
    test_reports = []
    if any_passed:
        test = frame[frame["market_date"].isin(split["sealed_test"])].copy()
        target = f"label_{args.horizon}d_cross_sectional_rank"
        return_column = f"label_{args.horizon}d_net_return_pct"
        for report in variant_reports:
            if not report["validation_passed"]:
                continue
            columns = report["feature_columns"]
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
                f"{report['feature_set']}_{report['algorithm']}_model.joblib"
            )
            with artifact.open("wb") as handle:
                pickle.dump(model, handle, protocol=pickle.HIGHEST_PROTOCOL)
            test_reports.append(
                {
                    "algorithm": report["algorithm"],
                    "feature_set": report["feature_set"],
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
        "model_family": "daily_options_cross_sectional_ranker",
        "universe": universe,
        "horizon_sessions": args.horizon,
        "panel": str(panel_path),
        "panel_sha256": expected_hash,
        "panel_rows": len(frame),
        "panel_dates": panel_dates,
        "split": {key: len(value) for key, value in split.items()},
        "split_dates": split,
        "sealed_test_rows": sealed_test_rows,
        "sealed_test_status": test_status,
        "feature_sets": list(FEATURE_SETS),
        "explicitly_excluded": manifest["explicitly_excluded"],
        "variants": variant_reports,
        "sealed_test_results": test_reports,
        "cost_pct": 0.25,
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
                "universe": universe,
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

