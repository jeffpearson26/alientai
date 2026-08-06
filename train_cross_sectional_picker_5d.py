from __future__ import annotations

"""Train and validation-gate the purged-CV five-session stock picker."""

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.research.cross_sectional_picker_5d import (
    LABEL_RETURN,
    evaluate_predictions,
    feature_matrix,
    passes_configured_filters,
    promotion_gate,
    purged_date_folds,
    ranked_feature_names,
    target_values,
)


MARKET_DATE_PATTERN = re.compile(r'"market_date"\s*:\s*"([^"]+)"')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "model_id",
        "horizon_sessions",
        "round_trip_cost_pct",
        "target_mode",
        "cross_validation",
        "selection",
        "filters",
        "model",
        "data",
    }
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"configuration keys missing: {missing}")
    if int(config["horizon_sessions"]) != 5:
        raise ValueError("this pipeline requires a five-session horizon")
    cv = config["cross_validation"]
    if int(cv["purge_sessions"]) < 5:
        raise ValueError("purge must cover the five-session label horizon")
    if int(cv["embargo_sessions"]) < 5:
        raise ValueError("embargo must be at least five sessions")
    selection = config["selection"]
    if not 0.0 < float(selection["top_quantile"]) <= 1.0:
        raise ValueError("top_quantile must be in (0, 1]")
    if int(selection["maximum_names"]) < 1:
        raise ValueError("maximum_names must be positive")
    if selection["weighting"] not in {"equal", "inverse_atr"}:
        raise ValueError("unsupported portfolio weighting")
    filters = config["filters"]
    if float(filters["minimum_price"]) <= 0.0:
        raise ValueError("minimum_price must be positive")
    if float(filters["minimum_average_dollar_volume"]) <= 0.0:
        raise ValueError("minimum_average_dollar_volume must be positive")
    if float(filters["minimum_relative_volume"]) < 0.0:
        raise ValueError("minimum_relative_volume cannot be negative")
    if float(filters["maximum_atr_pct"]) <= 0.0:
        raise ValueError("maximum_atr_pct must be positive")
    if config["target_mode"] not in {
        "cross_sectional_rank",
        "continuous_return",
        "binary_positive",
    } and not str(config["target_mode"]).startswith("binary_above_"):
        raise ValueError("unsupported target mode")
    return config


def scan_dates(path: Path) -> list[str]:
    dates = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            match = MARKET_DATE_PATTERN.search(line)
            if match is None:
                raise ValueError(f"market_date missing at line {line_number}")
            dates.add(match.group(1))
    return sorted(dates)


def read_rows(
    path: Path,
    allowed_dates: set[str],
    filters: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            match = MARKET_DATE_PATTERN.search(line)
            if match is None:
                raise ValueError(f"market_date missing at line {line_number}")
            if match.group(1) not in allowed_dates:
                continue
            row = json.loads(line)
            if passes_configured_filters(row, filters):
                rows.append(row)
    return rows


def lgb_parameters(
    config: Mapping[str, Any],
) -> dict[str, Any]:
    model = config["model"]
    target_mode = str(config["target_mode"])
    binary = target_mode.startswith("binary_")
    seed = int(model["seed"])
    return {
        "objective": "binary" if binary else "regression_l2",
        "metric": "binary_logloss" if binary else "l2",
        "learning_rate": float(model["learning_rate"]),
        "num_leaves": int(model["num_leaves"]),
        "min_data_in_leaf": int(model["min_data_in_leaf"]),
        "feature_fraction": float(model["feature_fraction"]),
        "bagging_fraction": float(model["bagging_fraction"]),
        "bagging_freq": 1,
        "lambda_l1": float(model["lambda_l1"]),
        "lambda_l2": float(model["lambda_l2"]),
        "max_depth": int(model["max_depth"]),
        "seed": seed,
        "feature_fraction_seed": seed,
        "bagging_seed": seed,
        "data_random_seed": seed,
        "deterministic": True,
        "force_col_wise": True,
        "verbosity": -1,
        "num_threads": int(model.get("num_threads", 0)),
    }


def train_booster(
    rows: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
    feature_names: Sequence[str],
) -> lgb.Booster:
    dataset = lgb.Dataset(
        feature_matrix(rows, feature_names),
        label=target_values(rows, str(config["target_mode"])),
        feature_name=list(feature_names),
        free_raw_data=True,
    )
    return lgb.train(
        lgb_parameters(config),
        dataset,
        num_boost_round=int(config["model"]["boosting_rounds"]),
    )


def transparent_scores(
    rows: Sequence[Mapping[str, Any]],
) -> np.ndarray:
    return np.asarray(
        [float(row["x5_transparent_composite_score"]) for row in rows]
    )


def evaluate(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    selection = config["selection"]
    return evaluate_predictions(
        rows,
        scores,
        top_quantile=float(selection["top_quantile"]),
        maximum_names=int(selection["maximum_names"]),
        horizon_sessions=int(config["horizon_sessions"]),
        weighting=str(selection["weighting"]),
    )


def write_selected(
    path: Path, rows: Sequence[Mapping[str, Any]]
) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            keep = {
                "symbol": row["symbol"],
                "market_date": row["market_date"],
                "model_score": row["model_score"],
                "model_score_cross_sectional_percentile": row[
                    "model_score_cross_sectional_percentile"
                ],
                LABEL_RETURN: row[LABEL_RETURN],
                "label_5d_exit_market_date": row[
                    "label_5d_exit_market_date"
                ],
            }
            handle.write(json.dumps(keep, sort_keys=True) + "\n")


def date_summary(dates: Sequence[str]) -> dict[str, Any]:
    return {
        "count": len(dates),
        "first": dates[0] if dates else None,
        "last": dates[-1] if dates else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--panel-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise ValueError("output root must be new and empty")

    config = load_config(args.config)
    manifest = json.loads(args.panel_manifest.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "complete"
        or int(manifest.get("horizon_sessions", 0)) != 5
        or not np.isclose(
            float(manifest.get("round_trip_cost_pct", -1.0)),
            float(config["round_trip_cost_pct"]),
            rtol=0.0,
            atol=1e-12,
        )
        or manifest.get("panel_sha256") != sha256(args.panel)
    ):
        raise ValueError("panel manifest contract mismatch")
    all_dates = scan_dates(args.panel)
    test_sessions = int(config["cross_validation"]["sealed_test_sessions"])
    embargo_sessions = int(config["cross_validation"]["embargo_sessions"])
    if len(all_dates) < test_sessions + embargo_sessions + 500:
        raise ValueError("insufficient chronology for CV and sealed test")
    test_dates = all_dates[-test_sessions:]
    development_dates = all_dates[: -test_sessions - embargo_sessions]
    gap_dates = all_dates[
        -test_sessions - embargo_sessions : -test_sessions
    ]
    development_rows = read_rows(
        args.panel, set(development_dates), config["filters"]
    )
    if not development_rows:
        raise ValueError("development rows are empty")

    names = ranked_feature_names()
    missing = sorted(
        {
            name
            for name in names
            if not any(name in row for row in development_rows)
        }
    )
    if missing:
        raise ValueError(f"ranked features missing: {missing}")
    forbidden = [
        name
        for name in names
        if name.startswith("label_") or "future" in name.lower()
    ]
    if forbidden:
        raise ValueError(f"future information entered model: {forbidden}")

    folds = purged_date_folds(
        development_rows,
        n_splits=int(config["cross_validation"]["folds"]),
        embargo_sessions=embargo_sessions,
    )
    oof_scores = np.full(len(development_rows), np.nan, dtype=float)
    fold_reports = []
    for fold in folds:
        train_set = set(fold.train_dates)
        test_set = set(fold.test_dates)
        train_rows = [
            row
            for row in development_rows
            if str(row["market_date"]) in train_set
        ]
        fold_indices = [
            index
            for index, row in enumerate(development_rows)
            if str(row["market_date"]) in test_set
        ]
        fold_rows = [development_rows[index] for index in fold_indices]
        booster = train_booster(train_rows, config, names)
        predictions = np.asarray(
            booster.predict(feature_matrix(fold_rows, names)), dtype=float
        )
        oof_scores[fold_indices] = predictions
        fold_metrics, _ = evaluate(fold_rows, predictions, config)
        fold_reports.append(
            {
                "fold": fold.fold,
                "train": date_summary(list(fold.train_dates)),
                "test": date_summary(list(fold.test_dates)),
                "purged_dates": list(fold.purged_dates),
                "embargo_dates": list(fold.embargo_dates),
                "train_rows": len(train_rows),
                "test_rows": len(fold_rows),
                "metrics": fold_metrics,
            }
        )
    if not np.all(np.isfinite(oof_scores)):
        missing_count = int(np.sum(~np.isfinite(oof_scores)))
        raise ValueError(f"OOF predictions incomplete: {missing_count}")

    learned_metrics, selected = evaluate(
        development_rows, oof_scores, config
    )
    transparent_metrics, transparent_selected = evaluate(
        development_rows,
        transparent_scores(development_rows),
        config,
    )
    passed, failures = promotion_gate(learned_metrics)

    args.output_root.mkdir(parents=True, exist_ok=True)
    final_model = train_booster(development_rows, config, names)
    model_path = args.output_root / "research_model.txt"
    final_model.save_model(str(model_path))
    selected_path = args.output_root / "oof_selections.jsonl.gz"
    transparent_path = (
        args.output_root / "transparent_oof_selections.jsonl.gz"
    )
    write_selected(selected_path, selected)
    write_selected(transparent_path, transparent_selected)

    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "RESEARCH_CANDIDATE" if passed else "RESEARCH_HOLD",
        "research_only": True,
        "execution_enabled": False,
        "model_id": config["model_id"],
        "method": (
            "LightGBM on date-local cross-sectional percentile-ranked "
            "technical features"
        ),
        "target_mode": config["target_mode"],
        "horizon_sessions": 5,
        "entry": manifest.get("entry"),
        "exit": manifest.get("exit"),
        "round_trip_cost_pct": config["round_trip_cost_pct"],
        "universe": manifest.get("candidates"),
        "candidate_count": manifest.get("candidate_count"),
        "feature_names": names,
        "feature_count": len(names),
        "config": str(args.config),
        "config_sha256": sha256(args.config),
        "panel": str(args.panel),
        "panel_sha256": sha256(args.panel),
        "panel_manifest": str(args.panel_manifest),
        "panel_manifest_sha256": sha256(args.panel_manifest),
        "development_dates": date_summary(development_dates),
        "pretest_embargo_dates": gap_dates,
        "sealed_test_dates": date_summary(test_dates),
        "cross_validation": {
            "type": "contiguous whole-date purged K-fold with embargo",
            "folds": len(folds),
            "label_overlap_purge": True,
            "purge_sessions": int(
                config["cross_validation"]["purge_sessions"]
            ),
            "embargo_sessions": embargo_sessions,
            "ordinary_random_kfold_used": False,
            "fold_reports": fold_reports,
        },
        "oof_metrics": learned_metrics,
        "transparent_baseline_oof_metrics": transparent_metrics,
        "promotion_gate": {
            "passed": passed,
            "failures": failures,
        },
        "model": str(model_path),
        "model_sha256": sha256(model_path),
        "oof_selections": str(selected_path),
        "oof_selections_sha256": sha256(selected_path),
        "transparent_oof_selections": str(transparent_path),
        "transparent_oof_selections_sha256": sha256(transparent_path),
        "sealed_test": {
            "status": "UNOPENED",
            "loaded": False,
            "reason": (
                "OOF promotion gate failed"
                if not passed
                else "OOF promotion gate passed; opening exactly once"
            ),
        },
        "daily_scoring_policy": {
            **config["selection"],
            "execution_decision": "AVOID",
            "reason": "research evidence never authorizes trading",
        },
        "limitations": [
            "The current fixed constituent files introduce survivorship and selection bias.",
            "Purged CV limits label overlap but cannot eliminate regime change.",
            "Technical cross-sectional edges are small and trading costs can erase them.",
            "Daily adjusted OHLCV does not model intraday fills or stop-loss paths.",
            "Promotion requires separate, append-only future evidence.",
        ],
    }
    if passed:
        test_rows = read_rows(
            args.panel, set(test_dates), config["filters"]
        )
        test_scores = np.asarray(
            final_model.predict(feature_matrix(test_rows, names)), dtype=float
        )
        test_metrics, test_selected = evaluate(
            test_rows, test_scores, config
        )
        test_path = args.output_root / "sealed_test_selections.jsonl.gz"
        write_selected(test_path, test_selected)
        report["sealed_test"] = {
            "status": "OPENED_ONCE",
            "loaded": True,
            "metrics": test_metrics,
            "selections": str(test_path),
            "selections_sha256": sha256(test_path),
        }

    report_path = args.output_root / "training_report.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "model_id": report["model_id"],
                "oof_metrics": report["oof_metrics"],
                "promotion_gate": report["promotion_gate"],
                "sealed_test": report["sealed_test"]["status"],
                "report": str(report_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
