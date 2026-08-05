from __future__ import annotations

"""Train the leakage-safe long-history AI/semi five-session successor model.

Model fitting, calibration, policy selection, and final testing use separate
whole-date partitions.  The sealed test is not loaded unless policy validation
passes the predeclared research gate.
"""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.research.score_calibration import (
    brier_score,
    expected_calibration_error,
    fit_isotonic,
)
from alientai_v2.research.catalyst_momentum_5d import engineer_rows


TARGET = "label_5d_net_return_pct"
LABEL_END = "label_5d_exit_market_date"
FEATURE_PREFIXES = (
    "technical_",
    "return_",
    "realized_volatility_",
    "sector_ai17_",
    "cm_technical_",
    "cm_risk_",
)
EMBARGO_SESSIONS = 5
MAX_DAILY_SELECTIONS = 5
PORTFOLIO_SLOTS = 25
POLICY_PERCENTILES = (60.0, 70.0, 80.0, 90.0, 95.0)
DIAGNOSTIC_COST_PCTS = (0.05, 0.10, 0.25)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def feature_names(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    names = sorted({
        name
        for row in rows
        for name in row
        if name.startswith(FEATURE_PREFIXES)
    })
    forbidden = [
        name for name in names
        if name.startswith("label_") or "future" in name.lower()
    ]
    if forbidden:
        raise ValueError(f"future fields entered feature set: {forbidden}")
    if not names:
        raise ValueError("no model features found")
    return names


def numeric(value: Any) -> float:
    if value is None:
        return np.nan
    if isinstance(value, bool):
        return float(value)
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan
    return result if np.isfinite(result) else np.nan


def matrix(rows: Sequence[Mapping[str, Any]], names: Sequence[str]) -> np.ndarray:
    return np.asarray(
        [[numeric(row.get(name)) for name in names] for row in rows],
        dtype=np.float32,
    )


def split_dates(dates: Iterable[str]) -> dict[str, set[str]]:
    ordered = sorted(set(str(value) for value in dates))
    if len(ordered) < 250:
        raise ValueError("at least 250 distinct market dates are required")
    boundaries = [
        int(len(ordered) * fraction)
        for fraction in (0.50, 0.65, 0.75, 0.85)
    ]
    train_end, fit_end, calibration_end, policy_end = boundaries

    def middle(left: int, right: int) -> set[str]:
        start = left + EMBARGO_SESSIONS if left else 0
        end = right - EMBARGO_SESSIONS
        if end <= start:
            raise ValueError("insufficient dates after two-sided embargo")
        return set(ordered[start:end])

    return {
        "train": middle(0, train_end),
        "fit_validation": middle(train_end, fit_end),
        "calibration": middle(fit_end, calibration_end),
        "policy_validation": middle(calibration_end, policy_end),
        "test": set(ordered[policy_end + EMBARGO_SESSIONS :]),
        "embargo": set(ordered) - (
            middle(0, train_end)
            | middle(train_end, fit_end)
            | middle(fit_end, calibration_end)
            | middle(calibration_end, policy_end)
            | set(ordered[policy_end + EMBARGO_SESSIONS :])
        ),
    }


def partition_rows(
    rows: Sequence[Mapping[str, Any]],
    dates: set[str],
) -> list[dict[str, Any]]:
    return [dict(row) for row in rows if str(row["market_date"]) in dates]


def apply_isotonic(
    scores: np.ndarray,
    blocks: Sequence[Mapping[str, float]],
) -> np.ndarray:
    uppers = np.asarray([float(block["upper_score"]) for block in blocks])
    probabilities = np.asarray([float(block["probability"]) for block in blocks])
    indices = np.searchsorted(uppers, scores.astype(float), side="left")
    return probabilities[np.minimum(indices, len(probabilities) - 1)]


def fit_ensemble_standardization(
    classifier_scores: np.ndarray,
    return_scores: np.ndarray,
) -> dict[str, float]:
    values = {
        "classifier_mean": float(np.mean(classifier_scores)),
        "classifier_std": float(np.std(classifier_scores)),
        "return_mean": float(np.mean(return_scores)),
        "return_std": float(np.std(return_scores)),
    }
    if values["classifier_std"] <= 0.0 or values["return_std"] <= 0.0:
        raise ValueError("ensemble calibration scores must have nonzero variance")
    return values


def ensemble_score(
    classifier_scores: np.ndarray,
    return_scores: np.ndarray,
    values: Mapping[str, float],
) -> np.ndarray:
    """Fixed equal-weight classifier/regressor ensemble; never policy-tuned."""
    return 0.5 * (
        (classifier_scores - values["classifier_mean"])
        / values["classifier_std"]
        + (return_scores - values["return_mean"])
        / values["return_std"]
    )


def select_daily(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    threshold: float,
    eligibility_field: str | None = None,
) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source, score in zip(rows, scores):
        if eligibility_field and not bool(source.get(eligibility_field)):
            continue
        if float(score) < threshold:
            continue
        row = dict(source)
        row["model_score"] = float(score)
        by_date[str(row["market_date"])].append(row)
    selected = []
    for market_date in sorted(by_date):
        ranked = sorted(
            by_date[market_date],
            key=lambda row: (-float(row["model_score"]), str(row["symbol"])),
        )
        selected.extend(ranked[:MAX_DAILY_SELECTIONS])
    return selected


def capital_scaled_drawdown(rows: Sequence[Mapping[str, Any]]) -> float | None:
    if not rows:
        return None
    by_exit: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_exit[str(row[LABEL_END])].append(float(row[TARGET]))
    equity = peak = 1.0
    worst = 0.0
    for exit_date in sorted(by_exit):
        daily_return = sum(by_exit[exit_date]) / PORTFOLIO_SLOTS / 100.0
        equity *= 1.0 + daily_return
        peak = max(peak, equity)
        worst = min(worst, equity / peak - 1.0)
    return worst * 100.0


def basic_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"signals": 0}
    net = np.asarray([float(row[TARGET]) for row in rows], dtype=float)
    gross = np.asarray(
        [float(row["label_5d_gross_return_pct"]) for row in rows], dtype=float
    )
    by_date: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_date[str(row["market_date"])].append(float(row[TARGET]))
    date_means = np.asarray([mean for mean in map(np.mean, by_date.values())])
    standard_error = (
        float(np.std(date_means, ddof=1) / np.sqrt(len(date_means)))
        if len(date_means) > 1 else None
    )
    symbol_counts = np.unique(
        [str(row["symbol"]) for row in rows], return_counts=True
    )[1]
    return {
        "signals": len(rows),
        "decision_dates": len(by_date),
        "symbols": len(symbol_counts),
        "mean_gross_return_pct": round(float(np.mean(gross)), 6),
        "median_gross_return_pct": round(float(np.median(gross)), 6),
        "mean_net_return_pct": round(float(np.mean(net)), 6),
        "median_net_return_pct": round(float(np.median(net)), 6),
        "win_rate_pct": round(float(np.mean(net > 0.0) * 100.0), 4),
        "target_2pct_rate_pct": round(float(np.mean(net >= 2.0) * 100.0), 4),
        "fifth_percentile_net_pct": round(float(np.percentile(net, 5)), 6),
        "worst_net_pct": round(float(np.min(net)), 6),
        "daily_cluster_mean_net_ci95_low_pct": (
            round(float(np.mean(date_means) - 1.96 * standard_error), 6)
            if standard_error is not None else None
        ),
        "daily_cluster_mean_net_ci95_high_pct": (
            round(float(np.mean(date_means) + 1.96 * standard_error), 6)
            if standard_error is not None else None
        ),
        "largest_symbol_share_pct": round(
            float(np.max(symbol_counts) / len(rows) * 100.0), 4
        ),
        "capital_scaled_max_drawdown_pct": round(
            float(capital_scaled_drawdown(rows)), 6
        ),
        "diagnostic_cost_sensitivity": {
            f"{cost:.2f}pct": {
                "mean_net_return_pct": round(float(np.mean(gross - cost)), 6),
                "median_net_return_pct": round(float(np.median(gross - cost)), 6),
                "win_rate_pct": round(
                    float(np.mean((gross - cost) > 0.0) * 100.0), 4
                ),
            }
            for cost in DIAGNOSTIC_COST_PCTS
        },
    }


def nonoverlap_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    dates = sorted({str(row["market_date"]) for row in rows})
    index = {market_date: position for position, market_date in enumerate(dates)}
    return {
        str(offset): basic_metrics([
            row for row in rows
            if index[str(row["market_date"])] % 5 == offset
        ])
        for offset in range(5)
    }


def policy_results(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    reference_scores: np.ndarray,
    eligibility_field: str | None = None,
) -> tuple[float | None, list[dict[str, Any]]]:
    results = []
    chosen: tuple[tuple[float, float, float], float] | None = None
    for percentile in POLICY_PERCENTILES:
        threshold = float(np.percentile(reference_scores, percentile))
        selected = select_daily(
            rows, scores, threshold, eligibility_field=eligibility_field
        )
        metrics = basic_metrics(selected)
        ci_low = metrics.get("daily_cluster_mean_net_ci95_low_pct")
        passes = (
            metrics.get("signals", 0) >= 50
            and metrics.get("decision_dates", 0) >= 30
            and metrics.get("mean_net_return_pct", -999.0) > 0.0
            and metrics.get("median_net_return_pct", -999.0) > 0.0
            and metrics.get("win_rate_pct", 0.0) >= 52.0
            and ci_low is not None and ci_low > 0.0
            and metrics.get("capital_scaled_max_drawdown_pct", -999.0) >= -20.0
            and metrics.get("largest_symbol_share_pct", 100.0) <= 25.0
        )
        record = {
            "score_percentile": percentile,
            "score_threshold": threshold,
            "passes_gate": passes,
            **metrics,
            "five_rotating_nonoverlap_cohorts": nonoverlap_metrics(selected),
        }
        results.append(record)
        key = (
            float(metrics.get("mean_net_return_pct", -999.0)),
            float(metrics.get("median_net_return_pct", -999.0)),
            float(metrics.get("win_rate_pct", 0.0)),
        )
        if passes and (chosen is None or key > chosen[0]):
            chosen = (key, threshold)
    return (chosen[1] if chosen else None), results


def date_range(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    dates = sorted({str(row["market_date"]) for row in rows})
    return {
        "rows": len(rows),
        "dates": len(dates),
        "first": dates[0] if dates else None,
        "last": dates[-1] if dates else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--eligibility",
        choices=("all", "technical_setup"),
        default="all",
        help="Optional predeclared catalyst-thesis technical setup gate.",
    )
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError("output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = engineer_rows([
        row for row in read_jsonl(args.input)
        if row.get(TARGET) is not None
        and row.get(LABEL_END)
        and row.get("return_60d_lag_pct") is not None
    ])
    eligibility_field = (
        "cm_technical_eligible"
        if args.eligibility == "technical_setup"
        else None
    )
    names = feature_names(rows)
    splits = split_dates(row["market_date"] for row in rows)
    parts = {
        name: partition_rows(rows, splits[name])
        for name in ("train", "fit_validation", "calibration", "policy_validation")
    }
    x = {name: matrix(part, names) for name, part in parts.items()}
    y = {
        name: np.asarray([float(row[TARGET]) > 0.0 for row in part], dtype=int)
        for name, part in parts.items()
    }

    classifier_train_data = lgb.Dataset(
        x["train"], label=y["train"], feature_name=names
    )
    classifier_fit_data = lgb.Dataset(
        x["fit_validation"], label=y["fit_validation"],
        reference=classifier_train_data, feature_name=names,
    )
    classifier_model = lgb.train(
        {
            "objective": "binary",
            "metric": ["binary_logloss", "auc"],
            "learning_rate": 0.02,
            "num_leaves": 15,
            "min_data_in_leaf": 80,
            "feature_fraction": 0.85,
            "bagging_fraction": 0.85,
            "bagging_freq": 1,
            "lambda_l1": 3.0,
            "lambda_l2": 12.0,
            "verbosity": -1,
            "seed": 42,
            "num_threads": -1,
            "force_col_wise": True,
        },
        classifier_train_data,
        num_boost_round=800,
        valid_sets=[classifier_fit_data],
        callbacks=[lgb.early_stopping(60, verbose=False), lgb.log_evaluation(0)],
    )
    return_train_data = lgb.Dataset(
        x["train"],
        label=np.asarray([float(row[TARGET]) for row in parts["train"]]),
        feature_name=names,
    )
    return_fit_data = lgb.Dataset(
        x["fit_validation"],
        label=np.asarray([
            float(row[TARGET]) for row in parts["fit_validation"]
        ]),
        reference=return_train_data,
        feature_name=names,
    )
    return_model = lgb.train(
        {
            "objective": "regression_l1",
            "metric": "l1",
            "learning_rate": 0.02,
            "num_leaves": 15,
            "min_data_in_leaf": 80,
            "feature_fraction": 0.85,
            "bagging_fraction": 0.85,
            "bagging_freq": 1,
            "lambda_l1": 3.0,
            "lambda_l2": 12.0,
            "verbosity": -1,
            "seed": 43,
            "num_threads": -1,
            "force_col_wise": True,
        },
        return_train_data,
        num_boost_round=800,
        valid_sets=[return_fit_data],
        callbacks=[lgb.early_stopping(60, verbose=False), lgb.log_evaluation(0)],
    )
    classifier_scores = {
        name: classifier_model.predict(
            values, num_iteration=classifier_model.best_iteration
        )
        for name, values in x.items()
    }
    return_scores = {
        name: return_model.predict(
            values, num_iteration=return_model.best_iteration
        )
        for name, values in x.items()
    }
    standardization = fit_ensemble_standardization(
        classifier_scores["calibration"], return_scores["calibration"]
    )
    combined_scores = {
        name: ensemble_score(
            classifier_scores[name], return_scores[name], standardization
        )
        for name in x
    }
    calibration_blocks = fit_isotonic(
        combined_scores["calibration"].tolist(), y["calibration"].tolist()
    )
    chosen_threshold, policies = policy_results(
        parts["policy_validation"],
        combined_scores["policy_validation"],
        combined_scores["calibration"],
        eligibility_field=eligibility_field,
    )

    classifier_model_path = args.output_dir / "classifier_model.txt"
    classifier_model.save_model(
        str(classifier_model_path),
        num_iteration=classifier_model.best_iteration,
    )
    return_model_path = args.output_dir / "return_model.txt"
    return_model.save_model(
        str(return_model_path), num_iteration=return_model.best_iteration
    )
    calibration_path = args.output_dir / "calibration.json"
    calibration_path.write_text(
        json.dumps(calibration_blocks, indent=2) + "\n", encoding="utf-8"
    )

    test_report: dict[str, Any]
    if chosen_threshold is None:
        test_report = {
            "status": "SEALED_UNLOADED",
            "reason": "no policy-validation threshold passed the frozen gate",
        }
        status = "RESEARCH_HOLD"
    else:
        test_rows = partition_rows(rows, splits["test"])
        test_x = matrix(test_rows, names)
        test_scores = ensemble_score(
            classifier_model.predict(
                test_x, num_iteration=classifier_model.best_iteration
            ),
            return_model.predict(
                test_x, num_iteration=return_model.best_iteration
            ),
            standardization,
        )
        selected_test = select_daily(
            test_rows,
            test_scores,
            chosen_threshold,
            eligibility_field=eligibility_field,
        )
        test_report = {
            "status": "OPENED_ONCE_AFTER_VALIDATION_PASS",
            **basic_metrics(selected_test),
            "five_rotating_nonoverlap_cohorts": nonoverlap_metrics(selected_test),
        }
        status = "FROZEN_PENDING_PROSPECTIVE"

    calibration_probabilities = apply_isotonic(
        combined_scores["calibration"], calibration_blocks
    )
    importance = sorted(
        [
            {"feature": name, "gain": round(float(gain), 6)}
            for name, gain in zip(
                names,
                (
                    classifier_model.feature_importance(importance_type="gain")
                    + return_model.feature_importance(importance_type="gain")
                ),
            )
        ],
        key=lambda item: item["gain"],
        reverse=True,
    )
    report = {
        "status": status,
        "research_only": True,
        "execution_enabled": False,
        "model_family": "AI/semi-17 five-session long-history successor",
        "input": str(args.input),
        "input_sha256": sha256(args.input),
        "symbols": sorted({str(row["symbol"]) for row in rows}),
        "rows": len(rows),
        "feature_names": names,
        "target": "net return after 0.25% round-trip cost > 0",
        "selection_eligibility": args.eligibility,
        "selection_eligibility_field": eligibility_field,
        "entry": "next regular-session open",
        "exit": "fifth subsequent regular-session close",
        "partitions": {
            name: date_range(part)
            for name, part in parts.items()
        } | {"test": {
            "rows_loaded": chosen_threshold is not None,
            "dates_reserved": len(splits["test"]),
            "first": min(splits["test"]) if splits["test"] else None,
            "last": max(splits["test"]) if splits["test"] else None,
        }},
        "embargo_sessions_each_side": EMBARGO_SESSIONS,
        "ensemble_contract": (
            "fixed equal weight of standardized positive-return classifier "
            "score and net-return regressor score"
        ),
        "ensemble_standardization_from_calibration": standardization,
        "classifier_best_iteration": int(classifier_model.best_iteration),
        "return_model_best_iteration": int(return_model.best_iteration),
        "classifier_model_path": str(classifier_model_path),
        "classifier_model_sha256": sha256(classifier_model_path),
        "return_model_path": str(return_model_path),
        "return_model_sha256": sha256(return_model_path),
        "calibration_path": str(calibration_path),
        "calibration_sha256": sha256(calibration_path),
        "calibration_metrics": {
            "brier_score": round(float(brier_score(
                calibration_probabilities.tolist(), y["calibration"].tolist()
            )), 8),
            "expected_calibration_error_10bin": round(float(
                expected_calibration_error(
                    calibration_probabilities.tolist(),
                    y["calibration"].tolist(),
                    bins=10,
                )
            ), 8),
        },
        "policy_gate": {
            "minimum_signals": 50,
            "minimum_decision_dates": 30,
            "mean_and_median_net_return_positive": True,
            "minimum_win_rate_pct": 52.0,
            "daily_cluster_ci95_low_positive": True,
            "capital_scaled_max_drawdown_floor_pct": -20.0,
            "maximum_largest_symbol_share_pct": 25.0,
            "chosen_score_threshold": chosen_threshold,
            "candidates": policies,
        },
        "test": test_report,
        "top_features": importance[:30],
        "catalyst_overlay_contract": (
            "rich 2026 catalyst/premarket/options fields are retained in the panel "
            "for a frozen prospective overlay, but excluded from this long-history "
            "base fit because equivalent older point-in-time coverage is absent"
        ),
        "warning": (
            "The current thematic universe has survivorship/selection bias. "
            "No trading is authorized."
        ),
    }
    report_path = args.output_dir / "training_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": status,
        "report": str(report_path),
        "rows": len(rows),
        "chosen_threshold": chosen_threshold,
        "test_status": test_report["status"],
    }, indent=2))


if __name__ == "__main__":
    main()
