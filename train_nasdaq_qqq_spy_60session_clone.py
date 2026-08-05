from __future__ import annotations

"""Train the research-only 60-session QQQ/SPY-relative daily clone."""

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


TARGET = "label_60d_net_return_pct"
GROSS = "label_60d_gross_return_pct"
LABEL_END = "label_60d_exit_market_date"
ALL_CONTEXT_PREFIXES = (
    "technical_",
    "return_",
    "realized_volatility_",
    "qqq_",
    "spy_",
    "relative_to_qqq_",
    "relative_to_spy_",
)
RELATIVE_SELECTION_PREFIXES = (
    "technical_",
    "return_",
    "realized_volatility_",
    "relative_to_qqq_",
    "relative_to_spy_",
)
EMBARGO_SESSIONS = 60
HAC_LAG_SESSIONS = 59
MAX_DAILY_SELECTIONS = 5
PORTFOLIO_SLOTS = 300
POLICY_PERCENTILES = (80.0, 90.0, 95.0, 97.5, 99.0)
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


def feature_names(
    rows: Sequence[Mapping[str, Any]],
    prefixes: Sequence[str],
) -> list[str]:
    names = sorted({
        name
        for row in rows
        for name in row
        if name.startswith(tuple(prefixes))
    })
    forbidden = [
        name for name in names
        if name.startswith("label_") or "future" in name.lower()
        or name.startswith(("model_news_", "model_call_", "model_option_"))
    ]
    if forbidden:
        raise ValueError(f"forbidden feature fields: {forbidden}")
    if not names:
        raise ValueError("no features found")
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
    if len(ordered) < 1500:
        raise ValueError("at least 1500 dates are required for a 60-session model")
    train_end, fit_end, calibration_end, policy_end = [
        int(len(ordered) * fraction)
        for fraction in (0.40, 0.60, 0.75, 0.90)
    ]

    def section(left: int, right: int) -> set[str]:
        start = left + EMBARGO_SESSIONS if left else 0
        end = right - EMBARGO_SESSIONS
        if end <= start:
            raise ValueError("partition is empty after two-sided 60-session embargo")
        return set(ordered[start:end])

    train = section(0, train_end)
    fit = section(train_end, fit_end)
    calibration = section(fit_end, calibration_end)
    policy = section(calibration_end, policy_end)
    test = set(ordered[policy_end + EMBARGO_SESSIONS :])
    assigned = train | fit | calibration | policy | test
    return {
        "train": train,
        "fit_validation": fit,
        "calibration": calibration,
        "policy_validation": policy,
        "test": test,
        "embargo": set(ordered) - assigned,
    }


def partition(
    rows: Sequence[Mapping[str, Any]], dates: set[str]
) -> list[dict[str, Any]]:
    return [dict(row) for row in rows if str(row["market_date"]) in dates]


def fit_standardization(
    classifier_scores: np.ndarray, return_scores: np.ndarray
) -> dict[str, float]:
    result = {
        "classifier_mean": float(np.mean(classifier_scores)),
        "classifier_std": float(np.std(classifier_scores)),
        "return_mean": float(np.mean(return_scores)),
        "return_std": float(np.std(return_scores)),
    }
    if result["classifier_std"] <= 0 or result["return_std"] <= 0:
        raise ValueError("ensemble components must have nonzero calibration variance")
    return result


def ensemble_score(
    classifier_scores: np.ndarray,
    return_scores: np.ndarray,
    values: Mapping[str, float],
) -> np.ndarray:
    return 0.5 * (
        (classifier_scores - values["classifier_mean"])
        / values["classifier_std"]
        + (return_scores - values["return_mean"]) / values["return_std"]
    )


def apply_isotonic(
    scores: np.ndarray, blocks: Sequence[Mapping[str, float]]
) -> np.ndarray:
    uppers = np.asarray([float(block["upper_score"]) for block in blocks])
    probabilities = np.asarray([float(block["probability"]) for block in blocks])
    indices = np.searchsorted(uppers, scores.astype(float), side="left")
    return probabilities[np.minimum(indices, len(probabilities) - 1)]


def select_daily(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    threshold: float,
) -> list[dict[str, Any]]:
    selected, _ = select_daily_with_diagnostics(rows, scores, threshold)
    return selected


def select_daily_with_diagnostics(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    threshold: float,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source, score in zip(rows, scores):
        if float(score) < threshold:
            continue
        row = dict(source)
        row["model_score"] = float(score)
        groups[str(row["market_date"])].append(row)
    output = []
    boundary_tie_abstentions = 0
    active_dates = 0
    for market_date in sorted(groups):
        active_dates += 1
        ranked = sorted(
            groups[market_date],
            key=lambda row: (-float(row["model_score"]), str(row["symbol"])),
        )
        if (
            len(ranked) > MAX_DAILY_SELECTIONS
            and np.isclose(
                float(ranked[MAX_DAILY_SELECTIONS - 1]["model_score"]),
                float(ranked[MAX_DAILY_SELECTIONS]["model_score"]),
                rtol=0.0,
                atol=1e-12,
            )
        ):
            boundary_tie_abstentions += 1
            continue
        output.extend(ranked[:MAX_DAILY_SELECTIONS])
    return output, {
        "active_dates_before_tie_guard": active_dates,
        "boundary_tie_abstentions": boundary_tie_abstentions,
    }


def newey_west_standard_error(values: np.ndarray, max_lag: int) -> float | None:
    if len(values) < max_lag + 5:
        return None
    centered = values - np.mean(values)
    count = len(values)
    long_run_variance = float(np.dot(centered, centered) / count)
    for lag in range(1, min(max_lag, count - 1) + 1):
        covariance = float(
            np.dot(centered[lag:], centered[:-lag]) / count
        )
        weight = 1.0 - lag / (max_lag + 1.0)
        long_run_variance += 2.0 * weight * covariance
    return float(np.sqrt(max(long_run_variance, 0.0) / count))


def capital_scaled_drawdown(rows: Sequence[Mapping[str, Any]]) -> float | None:
    if not rows:
        return None
    exits: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        exits[str(row[LABEL_END])].append(float(row[TARGET]))
    equity = peak = 1.0
    worst = 0.0
    for market_date in sorted(exits):
        portfolio_return = sum(exits[market_date]) / PORTFOLIO_SLOTS / 100.0
        equity *= 1.0 + portfolio_return
        peak = max(peak, equity)
        worst = min(worst, equity / peak - 1.0)
    return worst * 100.0


def basic_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"signals": 0}
    net = np.asarray([float(row[TARGET]) for row in rows])
    gross = np.asarray([float(row[GROSS]) for row in rows])
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        groups[str(row["market_date"])].append(float(row[TARGET]))
    dates = sorted(groups)
    date_means = np.asarray([float(np.mean(groups[date])) for date in dates])
    hac_se = newey_west_standard_error(date_means, HAC_LAG_SESSIONS)
    symbols, counts = np.unique(
        [str(row["symbol"]) for row in rows], return_counts=True
    )
    return {
        "signals": len(rows),
        "decision_dates": len(dates),
        "symbols": len(symbols),
        "mean_gross_return_pct": round(float(np.mean(gross)), 6),
        "median_gross_return_pct": round(float(np.median(gross)), 6),
        "mean_net_return_pct": round(float(np.mean(net)), 6),
        "median_net_return_pct": round(float(np.median(net)), 6),
        "win_rate_pct": round(float(np.mean(net > 0.0) * 100.0), 4),
        "target_10pct_rate_pct": round(float(np.mean(net >= 10.0) * 100.0), 4),
        "fifth_percentile_net_pct": round(float(np.percentile(net, 5)), 6),
        "worst_net_pct": round(float(np.min(net)), 6),
        "newey_west_lag_sessions": HAC_LAG_SESSIONS,
        "hac_mean_net_ci95_low_pct": (
            round(float(np.mean(date_means) - 1.96 * hac_se), 6)
            if hac_se is not None else None
        ),
        "hac_mean_net_ci95_high_pct": (
            round(float(np.mean(date_means) + 1.96 * hac_se), 6)
            if hac_se is not None else None
        ),
        "largest_symbol_share_pct": round(
            float(np.max(counts) / len(rows) * 100.0), 4
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


def nonoverlap_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    dates = sorted({str(row["market_date"]) for row in rows})
    positions = {date: index for index, date in enumerate(dates)}
    fold_metrics = [
        basic_metrics([
            row for row in rows
            if positions[str(row["market_date"])] % 60 == offset
        ])
        for offset in range(60)
    ]
    observed = [
        result for result in fold_metrics
        if result.get("signals", 0) > 0
    ]
    means = [
        float(result["mean_net_return_pct"]) for result in observed
    ]
    return {
        "observed_folds": len(observed),
        "positive_mean_folds": sum(value > 0.0 for value in means),
        "median_fold_mean_net_pct": (
            round(float(np.median(means)), 6) if means else None
        ),
        "worst_fold_mean_net_pct": (
            round(float(np.min(means)), 6) if means else None
        ),
        "folds": fold_metrics,
    }


def choose_policy(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    calibration_scores: np.ndarray,
) -> tuple[float | None, list[dict[str, Any]]]:
    output = []
    chosen: tuple[tuple[float, float, float], float] | None = None
    for percentile in POLICY_PERCENTILES:
        threshold = float(np.percentile(calibration_scores, percentile))
        selected, selection_diagnostics = select_daily_with_diagnostics(
            rows, scores, threshold
        )
        metrics = basic_metrics(selected)
        nonoverlap = nonoverlap_summary(selected)
        passes = (
            metrics.get("signals", 0) >= 100
            and metrics.get("decision_dates", 0) >= 60
            and metrics.get("mean_net_return_pct", -999.0) > 0.0
            and metrics.get("median_net_return_pct", -999.0) > 0.0
            and metrics.get("win_rate_pct", 0.0) >= 52.0
            and metrics.get("hac_mean_net_ci95_low_pct") is not None
            and metrics["hac_mean_net_ci95_low_pct"] > 0.0
            and metrics.get("capital_scaled_max_drawdown_pct", -999.0) >= -20.0
            and metrics.get("largest_symbol_share_pct", 100.0) <= 15.0
            and nonoverlap["observed_folds"] >= 45
            and nonoverlap["positive_mean_folds"] >= 36
            and nonoverlap["median_fold_mean_net_pct"] > 0.0
        )
        record = {
            "score_percentile": percentile,
            "score_threshold": threshold,
            "passes_gate": passes,
            **selection_diagnostics,
            **metrics,
            "sixty_rotating_nonoverlap_cohorts": nonoverlap,
        }
        output.append(record)
        key = (
            float(metrics.get("mean_net_return_pct", -999.0)),
            float(metrics.get("median_net_return_pct", -999.0)),
            float(metrics.get("win_rate_pct", 0.0)),
        )
        if passes and (chosen is None or key > chosen[0]):
            chosen = (key, threshold)
    return (chosen[1] if chosen else None), output


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
        "--feature-set",
        choices=("all_context", "relative_selection"),
        default="all_context",
    )
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError("output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    panel_manifest_path = args.input.with_suffix(".manifest.json")
    panel_manifest = json.loads(
        panel_manifest_path.read_text(encoding="utf-8")
    )
    if (
        panel_manifest.get("status") != "complete"
        or panel_manifest.get("horizon_sessions") != 60
        or panel_manifest.get("panel_sha256") != sha256(args.input)
    ):
        raise ValueError("panel manifest is invalid")
    rows = [
        row for row in read_jsonl(args.input)
        if row.get(TARGET) is not None
        and row.get(LABEL_END)
        and row.get("return_60d_lag_pct") is not None
    ]
    prefixes = (
        ALL_CONTEXT_PREFIXES
        if args.feature_set == "all_context"
        else RELATIVE_SELECTION_PREFIXES
    )
    names = feature_names(rows, prefixes)
    splits = split_dates(row["market_date"] for row in rows)
    parts = {
        name: partition(rows, splits[name])
        for name in ("train", "fit_validation", "calibration", "policy_validation")
    }
    x = {name: matrix(part, names) for name, part in parts.items()}
    positive = {
        name: np.asarray([float(row[TARGET]) > 0.0 for row in part], dtype=int)
        for name, part in parts.items()
    }

    classifier_train = lgb.Dataset(
        x["train"], label=positive["train"], feature_name=names
    )
    classifier_fit = lgb.Dataset(
        x["fit_validation"],
        label=positive["fit_validation"],
        reference=classifier_train,
        feature_name=names,
    )
    common_parameters = {
        "learning_rate": 0.02,
        "num_leaves": 15,
        "min_data_in_leaf": 100,
        "feature_fraction": 0.85,
        "bagging_fraction": 0.85,
        "bagging_freq": 1,
        "lambda_l1": 3.0,
        "lambda_l2": 15.0,
        "verbosity": -1,
        "num_threads": -1,
        "force_col_wise": True,
    }
    classifier_model = lgb.train(
        {
            **common_parameters,
            "objective": "binary",
            "metric": ["binary_logloss", "auc"],
            "seed": 42,
        },
        classifier_train,
        num_boost_round=1000,
        valid_sets=[classifier_fit],
        callbacks=[lgb.early_stopping(80, verbose=False), lgb.log_evaluation(0)],
    )
    return_train = lgb.Dataset(
        x["train"],
        label=np.asarray([float(row[TARGET]) for row in parts["train"]]),
        feature_name=names,
    )
    return_fit = lgb.Dataset(
        x["fit_validation"],
        label=np.asarray([
            float(row[TARGET]) for row in parts["fit_validation"]
        ]),
        reference=return_train,
        feature_name=names,
    )
    return_model = lgb.train(
        {
            **common_parameters,
            "objective": "regression_l1",
            "metric": "l1",
            "seed": 43,
        },
        return_train,
        num_boost_round=1000,
        valid_sets=[return_fit],
        callbacks=[lgb.early_stopping(80, verbose=False), lgb.log_evaluation(0)],
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
    standardization = fit_standardization(
        classifier_scores["calibration"], return_scores["calibration"]
    )
    combined = {
        name: ensemble_score(
            classifier_scores[name], return_scores[name], standardization
        )
        for name in x
    }
    blocks = fit_isotonic(
        combined["calibration"].tolist(),
        positive["calibration"].tolist(),
    )
    chosen_threshold, policies = choose_policy(
        parts["policy_validation"],
        combined["policy_validation"],
        combined["calibration"],
    )

    classifier_path = args.output_dir / "classifier_model.txt"
    return_path = args.output_dir / "return_model.txt"
    calibration_path = args.output_dir / "calibration.json"
    classifier_model.save_model(
        str(classifier_path), num_iteration=classifier_model.best_iteration
    )
    return_model.save_model(
        str(return_path), num_iteration=return_model.best_iteration
    )
    calibration_path.write_text(
        json.dumps(blocks, indent=2) + "\n", encoding="utf-8"
    )

    if chosen_threshold is None:
        test = {
            "status": "SEALED_UNLOADED",
            "reason": "no policy-validation threshold passed every frozen gate",
        }
        status = "RESEARCH_HOLD"
    else:
        test_rows = partition(rows, splits["test"])
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
        selected = select_daily(test_rows, test_scores, chosen_threshold)
        test = {
            "status": "OPENED_ONCE_AFTER_VALIDATION_PASS",
            **basic_metrics(selected),
            "sixty_rotating_nonoverlap_cohorts": nonoverlap_summary(selected),
        }
        status = "FROZEN_PENDING_PROSPECTIVE"

    calibration_probabilities = apply_isotonic(
        combined["calibration"], blocks
    )
    importance = sorted(
        [
            {"feature": name, "gain": round(float(gain), 6)}
            for name, gain in zip(
                names,
                classifier_model.feature_importance(importance_type="gain")
                + return_model.feature_importance(importance_type="gain"),
            )
        ],
        key=lambda item: item["gain"],
        reverse=True,
    )
    report = {
        "status": status,
        "research_only": True,
        "execution_enabled": False,
        "model_family": "Nasdaq-101 plus QQQ/SPY 60-session daily clone",
        "input": str(args.input),
        "input_sha256": sha256(args.input),
        "panel_manifest_sha256": sha256(panel_manifest_path),
        "rows": len(rows),
        "symbols": sorted({str(row["symbol"]) for row in rows}),
        "features": names,
        "feature_set": args.feature_set,
        "feature_prefixes": list(prefixes),
        "target": "60-session net return after 0.25% cost > 0",
        "entry": "next regular-session adjusted open",
        "exit": "60th subsequent adjusted close",
        "partitions": {
            name: date_range(part) for name, part in parts.items()
        } | {"test": {
            "rows_loaded": chosen_threshold is not None,
            "dates_reserved": len(splits["test"]),
            "first": min(splits["test"]) if splits["test"] else None,
            "last": max(splits["test"]) if splits["test"] else None,
        }},
        "embargo_sessions_each_side": EMBARGO_SESSIONS,
        "ensemble_contract": (
            "fixed equal weight of standardized positive-return classifier "
            "and expected-net-return regressor"
        ),
        "ensemble_standardization": standardization,
        "classifier_best_iteration": int(classifier_model.best_iteration),
        "return_model_best_iteration": int(return_model.best_iteration),
        "classifier_model_path": str(classifier_path),
        "classifier_model_sha256": sha256(classifier_path),
        "return_model_path": str(return_path),
        "return_model_sha256": sha256(return_path),
        "calibration_path": str(calibration_path),
        "calibration_sha256": sha256(calibration_path),
        "calibration_metrics": {
            "brier_score": round(float(brier_score(
                calibration_probabilities.tolist(),
                positive["calibration"].tolist(),
            )), 8),
            "expected_calibration_error_10bin": round(float(
                expected_calibration_error(
                    calibration_probabilities.tolist(),
                    positive["calibration"].tolist(),
                    bins=10,
                )
            ), 8),
        },
        "policy_gate": {
            "chosen_score_threshold": chosen_threshold,
            "candidates": policies,
            "requires_hac_ci95_low_positive": True,
            "requires_36_of_60_positive_nonoverlap_folds": True,
            "portfolio_slots": PORTFOLIO_SLOTS,
        },
        "test": test,
        "top_features": importance[:30],
        "catalyst_overlay": {
            "rows_available": panel_manifest.get("rows_with_catalyst_overlay", 0),
            "fields_retained_in_panel": True,
            "included_in_long_history_fit": False,
            "reason": (
                "only 48 sampled 2026 decision dates across 80 symbols are "
                "available; this is insufficient for a 60-session chronology "
                "with independent fit/calibration/policy/test partitions"
            ),
        },
        "warnings": [
            "current-membership universe creates survivorship bias",
            "adjacent 60-session labels overlap; HAC and rotating cohorts are required",
            "no paper or live trading is authorized",
        ],
    }
    report_path = args.output_dir / "training_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": status,
        "report": str(report_path),
        "rows": len(rows),
        "symbols": len(report["symbols"]),
        "chosen_threshold": chosen_threshold,
        "test_status": test["status"],
    }, indent=2))


if __name__ == "__main__":
    main()
