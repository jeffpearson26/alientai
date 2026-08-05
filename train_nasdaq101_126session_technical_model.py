from __future__ import annotations

"""Train and honestly gate the Nasdaq-101 six-month long-selection model."""

import argparse
import json
import math
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
from build_nasdaq_qqq_spy_60session_panel import load_adjusted_daily
from train_nasdaq_qqq_spy_60session_clone import (
    apply_isotonic,
    date_range,
    ensemble_score,
    feature_names,
    fit_standardization,
    matrix,
    newey_west_standard_error,
    read_jsonl,
    select_daily_with_diagnostics,
    sha256,
)


TARGET = "label_126d_net_return_pct"
GROSS = "label_126d_gross_return_pct"
LABEL_END = "label_126d_exit_market_date"
MODEL_TARGET = "model_excess_to_qqq_126d_pct"
HORIZON_SESSIONS = 126
EMBARGO_SESSIONS = 126
HAC_LAG_SESSIONS = 125
MAX_DAILY_SELECTIONS = 5
PORTFOLIO_SLOTS = MAX_DAILY_SELECTIONS * HORIZON_SESSIONS
POLICY_PERCENTILES = (90.0, 95.0, 97.5, 99.0)
FEATURE_PREFIXES = (
    "technical_",
    "lh_",
    "qqq_",
    "spy_",
    "relative_to_",
    "beta_to_",
    "correlation_to_",
    "rank_",
)
RANK_SOURCE_PREFIXES = (
    "technical_",
    "lh_return_",
    "lh_sma_",
    "lh_ema_",
    "lh_slope_",
    "lh_rsi_",
    "lh_money_",
    "lh_realized_",
    "lh_downside_",
    "lh_return_skew_",
    "lh_positive_",
    "lh_distance_",
    "lh_donchian_",
    "lh_max_drawdown_",
    "lh_latest_volume_",
    "lh_obv_",
    "lh_chaikin_",
    "lh_stochastic_",
    "lh_williams_",
    "relative_to_",
    "beta_to_",
    "correlation_to_",
)


def split_dates(
    dates: Iterable[str], decision_stride: int = 1
) -> dict[str, set[str]]:
    ordered = sorted(set(str(value) for value in dates))
    if len(ordered) < 900:
        raise ValueError("at least 900 sampled dates are required")
    embargo_dates = math.ceil(EMBARGO_SESSIONS / decision_stride)
    boundaries = [
        int(len(ordered) * fraction)
        for fraction in (0.45, 0.62, 0.76, 0.90)
    ]

    def section(left: int, right: int) -> set[str]:
        start = left + embargo_dates if left else 0
        end = right - embargo_dates
        if end <= start:
            raise ValueError("empty partition after 126-session embargo")
        return set(ordered[start:end])

    train = section(0, boundaries[0])
    fit = section(boundaries[0], boundaries[1])
    calibration = section(boundaries[1], boundaries[2])
    policy = section(boundaries[2], boundaries[3])
    test = set(ordered[boundaries[3] + embargo_dates :])
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


def percentile_ranks(values: np.ndarray) -> np.ndarray:
    ranks = np.full(len(values), np.nan, dtype=float)
    finite = np.flatnonzero(np.isfinite(values))
    if len(finite) == 1:
        ranks[finite[0]] = 0.5
    elif len(finite) > 1:
        ordered = finite[np.argsort(values[finite], kind="mergesort")]
        positions = np.linspace(0.0, 1.0, len(ordered))
        start = 0
        while start < len(ordered):
            end = start + 1
            while (
                end < len(ordered)
                and values[ordered[end]] == values[ordered[start]]
            ):
                end += 1
            ranks[ordered[start:end]] = float(
                np.mean(positions[start:end])
            )
            start = end
    return ranks


def add_cross_sectional_feature_ranks(
    rows: Sequence[dict[str, Any]],
) -> list[str]:
    sources = sorted(
        {
            name
            for row in rows[: min(500, len(rows))]
            for name in row
            if name.startswith(RANK_SOURCE_PREFIXES)
            and "above_sma_" not in name
            and "breakout_" not in name
        }
    )
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_date[str(row["market_date"])].append(row)
    for group in by_date.values():
        for name in sources:
            values = np.asarray(
                [
                    float(row[name])
                    if row.get(name) is not None
                    and np.isfinite(float(row[name]))
                    else np.nan
                    for row in group
                ],
                dtype=float,
            )
            ranks = percentile_ranks(values)
            for row, rank in zip(group, ranks):
                row[f"rank_{name}"] = (
                    float(rank) if np.isfinite(rank) else None
                )
    return [f"rank_{name}" for name in sources]


def cross_sectional_score_percentiles(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
) -> np.ndarray:
    output = np.full(len(rows), np.nan, dtype=float)
    by_date: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        by_date[str(row["market_date"])].append(index)
    for indices in by_date.values():
        values = np.asarray([float(scores[index]) for index in indices])
        ranks = percentile_ranks(values)
        for local, source_index in enumerate(indices):
            output[source_index] = ranks[local]
    return output


def selected_rows(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    threshold: float,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    selected, diagnostics = select_daily_with_diagnostics(
        rows, scores, threshold
    )
    return selected, diagnostics


def additive_mark_to_market_drawdown(
    rows: Sequence[Mapping[str, Any]],
    daily: Mapping[str, Sequence[Mapping[str, Any]]],
) -> float | None:
    """Cash-scaled daily drawdown with idle capital and fixed 1/630 slots."""
    if not rows:
        return None
    daily_pnl_pct: dict[str, float] = defaultdict(float)
    for row in rows:
        symbol = str(row["symbol"])
        candles = daily[symbol]
        positions = {
            str(candle["market_date"]): index
            for index, candle in enumerate(candles)
        }
        entry_date = str(row["label_entry_market_date"])
        exit_date = str(row[LABEL_END])
        if entry_date not in positions or exit_date not in positions:
            raise ValueError(f"missing mark-to-market path: {symbol}|{entry_date}")
        entry_index = positions[entry_date]
        exit_index = positions[exit_date]
        if exit_index - entry_index != HORIZON_SESSIONS - 1:
            raise ValueError(f"unexpected holding path: {symbol}|{entry_date}")
        entry_price = float(row["label_entry_next_adjusted_open"])
        prior_price = entry_price
        for index in range(entry_index, exit_index + 1):
            close = float(candles[index]["close"])
            daily_pnl_pct[str(candles[index]["market_date"])] += (
                (close - prior_price) / entry_price * 100.0 / PORTFOLIO_SLOTS
            )
            prior_price = close
        daily_pnl_pct[exit_date] -= (
            float(row["round_trip_cost_pct"]) / PORTFOLIO_SLOTS
        )
    equity = peak = 1.0
    worst = 0.0
    for market_date in sorted(daily_pnl_pct):
        equity += daily_pnl_pct[market_date] / 100.0
        peak = max(peak, equity)
        worst = min(worst, equity / peak - 1.0)
    return worst * 100.0


def basic_metrics(
    rows: Sequence[Mapping[str, Any]],
    daily: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    if not rows:
        return {"signals": 0}
    net = np.asarray([float(row[TARGET]) for row in rows], dtype=float)
    gross = np.asarray([float(row[GROSS]) for row in rows], dtype=float)
    by_date: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_date[str(row["market_date"])].append(float(row[TARGET]))
    date_means = np.asarray(
        [float(np.mean(by_date[date])) for date in sorted(by_date)], dtype=float
    )
    hac_se = newey_west_standard_error(date_means, HAC_LAG_SESSIONS)
    symbols, counts = np.unique(
        [str(row["symbol"]) for row in rows], return_counts=True
    )
    drawdown = additive_mark_to_market_drawdown(rows, daily)
    return {
        "signals": len(rows),
        "decision_dates": len(by_date),
        "symbols": len(symbols),
        "mean_gross_return_pct": round(float(np.mean(gross)), 6),
        "median_gross_return_pct": round(float(np.median(gross)), 6),
        "mean_net_return_pct": round(float(np.mean(net)), 6),
        "median_net_return_pct": round(float(np.median(net)), 6),
        "win_rate_pct": round(float(np.mean(net > 0.0) * 100.0), 4),
        "gain_10pct_rate_pct": round(float(np.mean(net >= 10.0) * 100.0), 4),
        "loss_10pct_rate_pct": round(float(np.mean(net <= -10.0) * 100.0), 4),
        "fifth_percentile_net_pct": round(float(np.percentile(net, 5)), 6),
        "worst_net_pct": round(float(np.min(net)), 6),
        "hac_lag_sessions": HAC_LAG_SESSIONS,
        "hac_mean_net_ci95_low_pct": (
            round(float(np.mean(date_means) - 1.96 * hac_se), 6)
            if hac_se is not None
            else None
        ),
        "hac_mean_net_ci95_high_pct": (
            round(float(np.mean(date_means) + 1.96 * hac_se), 6)
            if hac_se is not None
            else None
        ),
        "largest_symbol_share_pct": round(
            float(np.max(counts) / len(rows) * 100.0), 4
        ),
        "cash_scaled_mark_to_market_max_drawdown_pct": (
            round(float(drawdown), 6) if drawdown is not None else None
        ),
        "diagnostic_cost_sensitivity": {
            f"{cost:.2f}pct": {
                "mean_net_return_pct": round(float(np.mean(gross - cost)), 6),
                "median_net_return_pct": round(
                    float(np.median(gross - cost)), 6
                ),
                "win_rate_pct": round(
                    float(np.mean((gross - cost) > 0.0) * 100.0), 4
                ),
            }
            for cost in (0.10, 0.25, 0.50, 1.00)
        },
    }


def nonoverlap_summary(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    folds = []
    for offset in range(HORIZON_SESSIONS):
        sample = [
            row
            for row in rows
            if int(row["market_session_index"]) % HORIZON_SESSIONS == offset
        ]
        values = [float(row[TARGET]) for row in sample]
        folds.append(
            {
                "offset": offset,
                "signals": len(sample),
                "decision_dates": len(
                    {str(row["market_date"]) for row in sample}
                ),
                "mean_net_return_pct": (
                    round(float(np.mean(values)), 6) if values else None
                ),
                "win_rate_pct": (
                    round(float(np.mean(np.asarray(values) > 0.0) * 100.0), 4)
                    if values
                    else None
                ),
            }
        )
    observed = [row for row in folds if row["signals"] > 0]
    means = [float(row["mean_net_return_pct"]) for row in observed]
    return {
        "observed_folds": len(observed),
        "positive_mean_folds": sum(value > 0.0 for value in means),
        "median_fold_mean_net_pct": (
            round(float(np.median(means)), 6) if means else None
        ),
        "worst_fold_mean_net_pct": (
            round(float(np.min(means)), 6) if means else None
        ),
        "folds": folds,
    }


def choose_policy(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    daily: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[float | None, list[dict[str, Any]]]:
    candidates = []
    chosen: tuple[tuple[float, float, float], float] | None = None
    score_percentiles = cross_sectional_score_percentiles(rows, scores)
    for percentile in POLICY_PERCENTILES:
        threshold = percentile / 100.0
        selected, diagnostics = selected_rows(
            rows, score_percentiles, threshold
        )
        metrics = basic_metrics(selected, daily)
        nonoverlap = nonoverlap_summary(selected)
        passes = (
            metrics.get("signals", 0) >= 250
            and metrics.get("decision_dates", 0) >= 100
            and metrics.get("mean_net_return_pct", -999.0) > 0.0
            and metrics.get("median_net_return_pct", -999.0) > 0.0
            and metrics.get("win_rate_pct", 0.0) >= 52.0
            and metrics.get("hac_mean_net_ci95_low_pct") is not None
            and metrics["hac_mean_net_ci95_low_pct"] > 0.0
            and metrics.get(
                "cash_scaled_mark_to_market_max_drawdown_pct", -999.0
            )
            >= -20.0
            and metrics.get("largest_symbol_share_pct", 100.0) <= 12.0
            and nonoverlap["observed_folds"] >= 100
            and nonoverlap["positive_mean_folds"] >= 70
            and nonoverlap["median_fold_mean_net_pct"] > 0.0
        )
        record = {
            "score_percentile": percentile,
            "score_threshold": threshold,
            "passes_gate": passes,
            **diagnostics,
            **metrics,
            "126_rotating_nonoverlap_cohorts": nonoverlap,
        }
        candidates.append(record)
        key = (
            float(metrics.get("mean_net_return_pct", -999.0)),
            float(metrics.get("median_net_return_pct", -999.0)),
            float(metrics.get("win_rate_pct", 0.0)),
        )
        if passes and (chosen is None or key > chosen[0]):
            chosen = (key, threshold)
    return (chosen[1] if chosen else None), candidates


def load_daily_paths(
    daily_root: Path, symbols: Sequence[str]
) -> dict[str, list[dict[str, Any]]]:
    return {
        symbol: load_adjusted_daily(daily_root / f"{symbol}_daily.json")
        for symbol in symbols
    }


def add_qqq_relative_targets(
    rows: Sequence[dict[str, Any]],
    qqq_rows: Sequence[Mapping[str, Any]],
) -> None:
    qqq_by_date = {
        str(row["market_date"]): row for row in qqq_rows
    }
    for row in rows:
        entry_date = str(row["label_entry_market_date"])
        exit_date = str(row[LABEL_END])
        if entry_date not in qqq_by_date or exit_date not in qqq_by_date:
            raise ValueError(
                f"QQQ target path missing: {entry_date}|{exit_date}"
            )
        qqq_gross = (
            float(qqq_by_date[exit_date]["close"])
            / float(qqq_by_date[entry_date]["open"])
            - 1.0
        ) * 100.0
        row["model_qqq_126d_gross_return_pct"] = qqq_gross
        row[MODEL_TARGET] = float(row[GROSS]) - qqq_gross


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--daily-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
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
        or panel_manifest.get("horizon_sessions") != HORIZON_SESSIONS
        or panel_manifest.get("panel_sha256") != sha256(args.input)
    ):
        raise ValueError("invalid 126-session panel manifest")
    rows = [
        row
        for row in read_jsonl(args.input)
        if row.get(TARGET) is not None and row.get(LABEL_END)
    ]
    symbols = sorted({str(row["symbol"]) for row in rows})
    if len(symbols) != 101:
        raise ValueError("training panel must contain all 101 candidates")
    rank_features = add_cross_sectional_feature_ranks(rows)
    daily = load_daily_paths(args.daily_root, [*symbols, "QQQ"])
    add_qqq_relative_targets(rows, daily["QQQ"])
    names = feature_names(rows, FEATURE_PREFIXES)
    decision_stride = int(
        panel_manifest.get("decision_stride_market_sessions", 1)
    )
    splits = split_dates(
        (row["market_date"] for row in rows), decision_stride
    )
    parts = {
        name: partition(rows, splits[name])
        for name in (
            "train",
            "fit_validation",
            "calibration",
            "policy_validation",
        )
    }
    x = {name: matrix(part, names) for name, part in parts.items()}
    positive = {
        name: np.asarray(
            [float(row[MODEL_TARGET]) > 0.0 for row in part], dtype=int
        )
        for name, part in parts.items()
    }

    common = {
        "learning_rate": 0.02,
        "num_leaves": 15,
        "min_data_in_leaf": 200,
        "feature_fraction": 0.75,
        "bagging_fraction": 0.80,
        "bagging_freq": 1,
        "lambda_l1": 5.0,
        "lambda_l2": 20.0,
        "verbosity": -1,
        "num_threads": -1,
        "force_col_wise": True,
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
    classifier = lgb.train(
        {
            **common,
            "objective": "binary",
            "metric": ["binary_logloss", "auc"],
            "seed": 126,
        },
        classifier_train,
        num_boost_round=1200,
        valid_sets=[classifier_fit],
        callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(0)],
    )
    return_train = lgb.Dataset(
        x["train"],
        label=np.asarray([float(row[MODEL_TARGET]) for row in parts["train"]]),
        feature_name=names,
    )
    return_fit = lgb.Dataset(
        x["fit_validation"],
        label=np.asarray(
            [float(row[MODEL_TARGET]) for row in parts["fit_validation"]]
        ),
        reference=return_train,
        feature_name=names,
    )
    regressor = lgb.train(
        {
            **common,
            "objective": "regression_l1",
            "metric": "l1",
            "seed": 127,
        },
        return_train,
        num_boost_round=1200,
        valid_sets=[return_fit],
        callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(0)],
    )
    classifier_scores = {
        name: classifier.predict(
            values, num_iteration=classifier.best_iteration
        )
        for name, values in x.items()
    }
    return_scores = {
        name: regressor.predict(values, num_iteration=regressor.best_iteration)
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
    threshold, policies = choose_policy(
        parts["policy_validation"],
        combined["policy_validation"],
        daily,
    )

    classifier_path = args.output_dir / "classifier_model.txt"
    regressor_path = args.output_dir / "return_model.txt"
    calibration_path = args.output_dir / "calibration.json"
    classifier.save_model(
        str(classifier_path), num_iteration=classifier.best_iteration
    )
    regressor.save_model(
        str(regressor_path), num_iteration=regressor.best_iteration
    )
    calibration_path.write_text(
        json.dumps(blocks, indent=2) + "\n", encoding="utf-8"
    )

    if threshold is None:
        test = {
            "status": "SEALED_UNLOADED",
            "reason": "no policy-validation threshold passed every frozen gate",
        }
        status = "RESEARCH_HOLD"
    else:
        test_rows = partition(rows, splits["test"])
        test_x = matrix(test_rows, names)
        test_scores = ensemble_score(
            classifier.predict(
                test_x, num_iteration=classifier.best_iteration
            ),
            regressor.predict(
                test_x, num_iteration=regressor.best_iteration
            ),
            standardization,
        )
        selected, diagnostics = selected_rows(
            test_rows, test_scores, threshold
        )
        test = {
            "status": "OPENED_ONCE_AFTER_VALIDATION_PASS",
            **diagnostics,
            **basic_metrics(selected, daily),
            "126_rotating_nonoverlap_cohorts": nonoverlap_summary(selected),
        }
        status = "FROZEN_PENDING_PROSPECTIVE"

    calibrated = apply_isotonic(combined["calibration"], blocks)
    importance = sorted(
        [
            {"feature": name, "gain": round(float(gain), 6)}
            for name, gain in zip(
                names,
                classifier.feature_importance(importance_type="gain")
                + regressor.feature_importance(importance_type="gain"),
            )
        ],
        key=lambda row: row["gain"],
        reverse=True,
    )
    report = {
        "status": status,
        "research_only": True,
        "execution_enabled": False,
        "model_family": "Nasdaq-101 comprehensive technical six-month long selector",
        "input": str(args.input),
        "input_sha256": sha256(args.input),
        "panel_manifest_sha256": sha256(panel_manifest_path),
        "rows": len(rows),
        "symbols": symbols,
        "candidate_count": len(symbols),
        "context_only_symbols": ["QQQ", "SPY"],
        "features": names,
        "feature_count": len(names),
        "cross_sectional_rank_features": rank_features,
        "model_target": (
            "126-session gross return minus QQQ 126-session gross return"
        ),
        "selection_gate_target": (
            "positive absolute 126-session net return after 0.25% cost"
        ),
        "entry": "next regular-session adjusted open",
        "exit": "126th subsequent adjusted close",
        "partitions": {
            name: date_range(part) for name, part in parts.items()
        }
        | {
            "test": {
                "rows_loaded": threshold is not None,
                "dates_reserved": len(splits["test"]),
                "first": min(splits["test"]) if splits["test"] else None,
                "last": max(splits["test"]) if splits["test"] else None,
            }
        },
        "embargo_sessions_each_side": EMBARGO_SESSIONS,
        "historical_decision_stride_market_sessions": decision_stride,
        "ensemble": (
            "fixed equal-weight standardized positive-return classifier "
            "plus expected-net-return regressor"
        ),
        "ensemble_standardization": standardization,
        "classifier_best_iteration": int(classifier.best_iteration),
        "return_model_best_iteration": int(regressor.best_iteration),
        "classifier_model_path": str(classifier_path),
        "classifier_model_sha256": sha256(classifier_path),
        "return_model_path": str(regressor_path),
        "return_model_sha256": sha256(regressor_path),
        "calibration_path": str(calibration_path),
        "calibration_sha256": sha256(calibration_path),
        "calibration_metrics": {
            "brier_score": round(
                float(
                    brier_score(
                        calibrated.tolist(),
                        positive["calibration"].tolist(),
                    )
                ),
                8,
            ),
            "expected_calibration_error_10bin": round(
                float(
                    expected_calibration_error(
                        calibrated.tolist(),
                        positive["calibration"].tolist(),
                        bins=10,
                    )
                ),
                8,
            ),
        },
        "policy_gate": {
            "chosen_score_threshold": threshold,
            "threshold_semantics": (
                "within-decision-date cross-sectional model-score percentile"
            ),
            "candidates": policies,
            "portfolio_slots": PORTFOLIO_SLOTS,
            "drawdown_contract": (
                "daily mark-to-market, fixed 1/630 slot weight, idle cash unchanged"
            ),
        },
        "test": test,
        "top_features": importance[:40],
        "warnings": [
            "current June 2026 membership creates survivorship bias",
            "the model is a research selector, not evidence of future profitability",
            "adjacent outcomes overlap; HAC and 126 calendar-aligned folds are required",
            "no paper or live trading is authorized",
        ],
    }
    report_path = args.output_dir / "training_report.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": status,
                "rows": len(rows),
                "features": len(names),
                "chosen_threshold": threshold,
                "test_status": test["status"],
                "report": str(report_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
