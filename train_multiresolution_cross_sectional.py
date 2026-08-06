from __future__ import annotations

"""Purged historical screening for the multi-resolution stock ranker."""

import argparse
import hashlib
import json
import pickle
from pathlib import Path
from typing import Any, Iterable

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb

from alientai_v2.research.multiresolution_cross_sectional import (
    CONTEXT_FEATURES,
    DAILY_FEATURES,
    FEATURE_SETS,
    FIVE_MINUTE_FEATURES,
    NEWS_FEATURES,
    OPTION_FEATURES,
    date_spearman,
    purged_date_folds,
    selection_metrics,
)


POLICY_THRESHOLDS = (0.85, 0.90, 0.95)
ALGORITHMS = ("lightgbm", "xgboost")
MIN_FULL_NEWS_DATES = 60
MIN_PANEL_DATES = {5: 60, 20: 120}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def feature_columns(feature_set: str) -> list[str]:
    raw = FEATURE_SETS[feature_set]
    output = []
    for name in raw:
        if (
            name in CONTEXT_FEATURES
            or name in {"option_available", "news_available"}
        ):
            output.append(name)
        else:
            output.append(f"rank_{name}")
    return output


def make_model(algorithm: str) -> Any:
    if algorithm == "lightgbm":
        return NativeLightGBM()
    if algorithm == "xgboost":
        return NativeXGBoost()
    raise ValueError(f"unsupported algorithm: {algorithm}")


class NativeLightGBM:
    def __init__(self) -> None:
        self.booster: lgb.Booster | None = None

    def fit(self, values: np.ndarray, target: pd.Series) -> "NativeLightGBM":
        dataset = lgb.Dataset(values, label=np.asarray(target, dtype=float))
        self.booster = lgb.train(
            {
                "objective": "regression",
                "metric": "l2",
                "learning_rate": 0.035,
                "num_leaves": 15,
                "max_depth": 5,
                "min_data_in_leaf": 40,
                "bagging_fraction": 0.80,
                "bagging_freq": 1,
                "feature_fraction": 0.80,
                "lambda_l1": 0.25,
                "lambda_l2": 2.0,
                "seed": 20260806,
                "num_threads": 0,
                "verbosity": -1,
            },
            dataset,
            num_boost_round=160,
        )
        return self

    def predict(self, values: np.ndarray) -> np.ndarray:
        if self.booster is None:
            raise ValueError("LightGBM model is not fit")
        return np.asarray(self.booster.predict(values), dtype=float)


class NativeXGBoost:
    def __init__(self) -> None:
        self.booster: xgb.Booster | None = None

    def fit(self, values: np.ndarray, target: pd.Series) -> "NativeXGBoost":
        matrix = xgb.DMatrix(values, label=np.asarray(target, dtype=float))
        self.booster = xgb.train(
            {
                "objective": "reg:squarederror",
                "eta": 0.035,
                "max_depth": 4,
                "min_child_weight": 20.0,
                "subsample": 0.80,
                "colsample_bytree": 0.80,
                "alpha": 0.25,
                "lambda": 2.0,
                "seed": 20260806,
                "tree_method": "hist",
                "nthread": -1,
            },
            matrix,
            num_boost_round=180,
        )
        return self

    def predict(self, values: np.ndarray) -> np.ndarray:
        if self.booster is None:
            raise ValueError("XGBoost model is not fit")
        return np.asarray(self.booster.predict(xgb.DMatrix(values)), dtype=float)


def matrix(frame: pd.DataFrame, columns: Iterable[str]) -> np.ndarray:
    return (
        frame[list(columns)]
        .apply(pd.to_numeric, errors="coerce")
        .to_numpy(dtype=np.float32)
    )


def validation_gate(metrics: dict[str, Any], mean_ic: float | None) -> dict:
    ci = metrics["clustered_mean_ci"]
    checks = {
        "minimum_100_signals": metrics["signals"] >= 100,
        "minimum_20_dates": metrics["dates"] >= 20,
        "positive_mean_net": (metrics["mean_net_return_pct"] or -np.inf) > 0.0,
        "positive_median_net": (
            metrics["median_net_return_pct"] or -np.inf
        )
        > 0.0,
        "win_rate_at_least_50": (metrics["win_rate_pct"] or 0.0) >= 50.0,
        "positive_rank_ic": (mean_ic or -np.inf) >= 0.01,
        "positive_top_minus_bottom": (
            metrics["top_minus_bottom_mean_pct"] or -np.inf
        )
        > 0.0,
        "positive_clustered_lower_95": (
            ci.get("lower_95")
            if ci.get("lower_95") is not None
            else -np.inf
        )
        > 0.0,
    }
    return {"passed": all(checks.values()), "checks": checks}


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
            ["market_date", f"label_{horizon}d_entry_date", f"label_{horizon}d_exit_date"]
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
        gate = validation_gate(metrics, mean_ic)
        policies.append(
            {
                "threshold": threshold,
                "metrics": metrics,
                "gate": gate,
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


def news_readiness(
    manifest: dict[str, Any], universe: str
) -> dict[str, Any]:
    threshold = 0.75 if universe == "nasdaq100" else 0.90
    by_date = manifest["coverage"]["news_coverage_by_date"]
    complete = sorted(
        date for date, coverage in by_date.items() if coverage >= threshold
    )
    return {
        "minimum_coverage_fraction": threshold,
        "complete_dates": len(complete),
        "minimum_required_dates": MIN_FULL_NEWS_DATES,
        "first_complete_date": complete[0] if complete else None,
        "last_complete_date": complete[-1] if complete else None,
        "ready": len(complete) >= MIN_FULL_NEWS_DATES,
        "blocker": (
            None
            if len(complete) >= MIN_FULL_NEWS_DATES
            else (
                f"only {len(complete)} dates meet {threshold:.0%} timestamped "
                f"news coverage; {MIN_FULL_NEWS_DATES} required"
            )
        ),
    }


def split_dates(frame: pd.DataFrame, horizon: int) -> dict[str, list[str]]:
    dates = sorted(frame["market_date"].astype(str).unique())
    minimum = MIN_PANEL_DATES[horizon]
    if len(dates) < minimum:
        raise ValueError(f"only {len(dates)} dates; {minimum} required")
    test_count = max(10, int(np.ceil(len(dates) * 0.15)))
    test = dates[-test_count:]
    test_start = len(dates) - test_count
    embargo_start = max(0, test_start - horizon)
    embargo = dates[embargo_start:test_start]
    development = dates[:embargo_start]
    if len(development) < 30:
        raise ValueError("fewer than 30 development dates after test embargo")
    return {
        "development": development,
        "pre_test_embargo": embargo,
        "sealed_test": test,
    }


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
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise ValueError("panel manifest is not complete")
    expected_hash = manifest["artifacts"]["panel"]["sha256"]
    if sha256(panel_path) != expected_hash:
        raise ValueError("panel hash mismatch")
    universe = str(manifest["universe"])
    frame = pd.read_csv(panel_path)
    if len(frame) != int(manifest["rows"]):
        raise ValueError("panel row count mismatch")
    if frame.duplicated(["market_date", "symbol"]).any():
        raise ValueError("duplicate panel keys")
    panel_dates = int(frame["market_date"].nunique())
    minimum_dates = MIN_PANEL_DATES[args.horizon]
    news_status = news_readiness(manifest, universe)
    if panel_dates < minimum_dates:
        blocker = (
            f"only {panel_dates} common point-in-time dates are available; "
            f"{minimum_dates} are required for the {args.horizon}-session "
            "purge, embargo, and sealed-test geometry"
        )
        report = {
            "status": "BLOCKED_INSUFFICIENT_HISTORY",
            "model_family": "multiresolution_cross_sectional_ranker",
            "universe": universe,
            "horizon_sessions": args.horizon,
            "panel": str(panel_path),
            "panel_sha256": expected_hash,
            "panel_rows": len(frame),
            "panel_dates": panel_dates,
            "minimum_required_dates": minimum_dates,
            "exact_blocker": blocker,
            "news_readiness": news_status,
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
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "universe": universe,
                    "horizon_sessions": args.horizon,
                    "blocker": blocker,
                    "report": str(report_path),
                },
                indent=2,
            )
        )
        return
    split = split_dates(frame, args.horizon)
    development = frame[
        frame["market_date"].isin(split["development"])
    ].copy()
    sealed_test_rows = int(
        frame["market_date"].isin(split["sealed_test"]).sum()
    )

    feature_sets = [
        "daily_only",
        "daily_plus_5minute",
        "daily_5minute_options",
    ]
    blocked_feature_sets = {}
    if news_status["ready"]:
        feature_sets.append("daily_5minute_options_news")
    else:
        blocked_feature_sets["daily_5minute_options_news"] = news_status[
            "blocker"
        ]

    variant_reports = []
    any_passed = False
    for feature_set in feature_sets:
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
            model.fit(matrix(development, columns), development[target].astype(float))
            test["model_score"] = model.predict(matrix(test, columns))
            threshold = report["selected_validation_policy"]["threshold"]
            metrics = selection_metrics(
                test,
                score_column="model_score",
                return_column=return_column,
                threshold=threshold,
            )
            mean_ic, ic_dates = date_spearman(test, "model_score", target)
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
        "model_family": "multiresolution_cross_sectional_ranker",
        "universe": universe,
        "horizon_sessions": args.horizon,
        "panel": str(panel_path),
        "panel_sha256": expected_hash,
        "panel_rows": len(frame),
        "panel_dates": int(frame["market_date"].nunique()),
        "split": {key: len(value) for key, value in split.items()},
        "split_dates": split,
        "sealed_test_rows": sealed_test_rows,
        "sealed_test_status": test_status,
        "news_readiness": news_status,
        "blocked_feature_sets": blocked_feature_sets,
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
                "panel_dates": report["panel_dates"],
                "development_dates": report["split"]["development"],
                "sealed_test_status": test_status,
                "news_feature_set": (
                    "tested"
                    if news_status["ready"]
                    else f"blocked: {news_status['blocker']}"
                ),
                "report": str(report_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
