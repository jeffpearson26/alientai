from __future__ import annotations

"""Core methods for the production-style five-session stock picker.

This module is deliberately research-only.  It contains no broker, order, or
engine integration.  Training rows and live snapshots share the exact same
date-local feature-ranking implementation.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from alientai_v2.research.cross_sectional_technical_5d import (
    RANK_FEATURES,
    TRANSPARENT_WEIGHTS,
    eligibility,
    percentile_ranks,
    technical_features,
)


LABEL_RANK = "label_5d_cross_sectional_return_rank"
LABEL_RETURN = "label_5d_net_return_pct"
LABEL_EXIT_DATE = "label_5d_exit_market_date"


@dataclass(frozen=True)
class PurgedFold:
    fold: int
    train_dates: tuple[str, ...]
    test_dates: tuple[str, ...]
    purged_dates: tuple[str, ...]
    embargo_dates: tuple[str, ...]


def ranked_feature_names() -> list[str]:
    """Return the model inputs; every predictive input is date-local."""
    return [f"rank_{name}" for name in RANK_FEATURES]


def numeric(value: Any) -> float:
    if value is None:
        return np.nan
    try:
        output = float(value)
    except (TypeError, ValueError):
        return np.nan
    return output if np.isfinite(output) else np.nan


def feature_matrix(
    rows: Sequence[Mapping[str, Any]],
    names: Sequence[str] | None = None,
) -> np.ndarray:
    selected = list(names or ranked_feature_names())
    return np.asarray(
        [[numeric(row.get(name)) for name in selected] for row in rows],
        dtype=np.float32,
    )


def target_values(
    rows: Sequence[Mapping[str, Any]], mode: str
) -> np.ndarray:
    if mode == "cross_sectional_rank":
        return np.asarray([float(row[LABEL_RANK]) for row in rows])
    if mode == "continuous_return":
        return np.asarray([float(row[LABEL_RETURN]) for row in rows])
    if mode == "binary_positive":
        return np.asarray(
            [float(row[LABEL_RETURN]) > 0.0 for row in rows], dtype=float
        )
    if mode.startswith("binary_above_"):
        threshold = float(mode.removeprefix("binary_above_"))
        return np.asarray(
            [float(row[LABEL_RETURN]) > threshold for row in rows],
            dtype=float,
        )
    raise ValueError(f"unsupported target mode: {mode}")


def passes_configured_filters(
    row: Mapping[str, Any], filters: Mapping[str, Any]
) -> bool:
    """Apply the frozen liquidity and risk filters to panel or live rows."""
    if row.get("x5_eligible") is not True:
        return False
    checks = (
        float(row["x5_decision_price"])
        >= float(filters["minimum_price"]),
        float(row["x5_average_dollar_volume_20d"])
        >= float(filters["minimum_average_dollar_volume"]),
        float(row["x5_relative_volume_20d"])
        >= float(filters["minimum_relative_volume"]),
        float(row["x5_atr_14_pct"])
        <= float(filters["maximum_atr_pct"]),
    )
    return all(checks)


def add_feature_ranks(rows: Sequence[dict[str, Any]]) -> None:
    """Add cross-sectional ranks without requiring or inspecting labels."""
    if not rows:
        raise ValueError("cannot rank an empty snapshot")
    dates = {str(row["market_date"]) for row in rows}
    if len(dates) != 1:
        raise ValueError("snapshot ranking requires exactly one market date")
    for feature in RANK_FEATURES:
        values = np.asarray(
            [numeric(row.get(feature)) for row in rows], dtype=float
        )
        ranks = percentile_ranks(values)
        for row, rank in zip(rows, ranks):
            row[f"rank_{feature}"] = (
                None if not np.isfinite(rank) else float(rank)
            )
    for row in rows:
        components = [
            (row.get(name), weight)
            for name, weight in TRANSPARENT_WEIGHTS.items()
        ]
        row["x5_transparent_composite_score"] = (
            None
            if any(value is None for value, _ in components)
            else float(
                sum(float(value) * weight for value, weight in components)
            )
        )


def _date_exit_map(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    output: dict[str, str] = {}
    for row in rows:
        market_date = str(row["market_date"])
        exit_date = str(row[LABEL_EXIT_DATE])
        if exit_date <= market_date:
            raise ValueError(
                f"non-forward label interval: {market_date}|{exit_date}"
            )
        output[market_date] = max(output.get(market_date, ""), exit_date)
    return output


def purged_date_folds(
    rows: Sequence[Mapping[str, Any]],
    *,
    n_splits: int,
    embargo_sessions: int,
) -> list[PurgedFold]:
    """Build contiguous date folds with label-overlap purge and embargo.

    A training date before a test fold is removed when its five-session label
    interval reaches into the test interval.  Dates immediately following the
    test fold are embargoed.  All rows from a date stay in the same partition.
    """
    if n_splits < 3:
        raise ValueError("purged cross-validation requires at least 3 folds")
    if embargo_sessions < 0:
        raise ValueError("embargo_sessions cannot be negative")
    exits = _date_exit_map(rows)
    dates = sorted(exits)
    if len(dates) < n_splits * 20:
        raise ValueError("insufficient dates for requested purged folds")
    positions = {value: index for index, value in enumerate(dates)}
    chunks = [
        tuple(str(value) for value in chunk)
        for chunk in np.array_split(np.asarray(dates, dtype=object), n_splits)
        if len(chunk)
    ]
    folds: list[PurgedFold] = []
    for fold_number, test_dates in enumerate(chunks):
        test_set = set(test_dates)
        test_start = test_dates[0]
        test_end = test_dates[-1]
        end_index = positions[test_end]
        embargo = set(
            dates[
                end_index
                + 1 : end_index
                + 1
                + embargo_sessions
            ]
        )
        purged = {
            market_date
            for market_date in dates
            if market_date < test_start and exits[market_date] >= test_start
        }
        train = tuple(
            market_date
            for market_date in dates
            if market_date not in test_set
            and market_date not in embargo
            and market_date not in purged
        )
        if not train:
            raise ValueError(f"fold {fold_number} has no training dates")
        folds.append(
            PurgedFold(
                fold=fold_number,
                train_dates=train,
                test_dates=test_dates,
                purged_dates=tuple(sorted(purged)),
                embargo_dates=tuple(sorted(embargo)),
            )
        )
    return folds


def date_local_score_percentiles(
    rows: Sequence[Mapping[str, Any]], scores: np.ndarray
) -> np.ndarray:
    if len(rows) != len(scores):
        raise ValueError("row/score length mismatch")
    output = np.full(len(rows), np.nan, dtype=float)
    groups: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        groups[str(row["market_date"])].append(index)
    for indices in groups.values():
        ranks = percentile_ranks(
            np.asarray([float(scores[index]) for index in indices])
        )
        for index, rank in zip(indices, ranks):
            output[index] = rank
    return output


def selected_indices(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    *,
    top_quantile: float,
    maximum_names: int,
    highest: bool = True,
) -> tuple[list[int], dict[str, int]]:
    if not 0.0 < top_quantile <= 1.0:
        raise ValueError("top_quantile must be in (0, 1]")
    if maximum_names < 1:
        raise ValueError("maximum_names must be positive")
    percentiles = date_local_score_percentiles(rows, scores)
    threshold = 1.0 - top_quantile
    groups: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        qualifies = (
            percentiles[index] >= threshold
            if highest
            else percentiles[index] <= top_quantile
        )
        if qualifies:
            groups[str(row["market_date"])].append(index)
    selected: list[int] = []
    tie_abstentions = 0
    for market_date in sorted(groups):
        ranked = sorted(
            groups[market_date],
            key=lambda index: (
                -float(scores[index])
                if highest
                else float(scores[index]),
                str(rows[index]["symbol"]),
            ),
        )
        if (
            len(ranked) > maximum_names
            and np.isclose(
                float(scores[ranked[maximum_names - 1]]),
                float(scores[ranked[maximum_names]]),
                rtol=0.0,
                atol=1e-12,
            )
        ):
            tie_abstentions += 1
            continue
        selected.extend(ranked[:maximum_names])
    return selected, {
        "selected_dates": len(groups) - tie_abstentions,
        "boundary_tie_abstentions": tie_abstentions,
    }


def _rank_ic(
    rows: Sequence[Mapping[str, Any]], scores: np.ndarray
) -> dict[str, Any]:
    score_ranks = date_local_score_percentiles(rows, scores)
    groups: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        groups[str(row["market_date"])].append(index)
    values: list[float] = []
    for indices in groups.values():
        if len(indices) < 5:
            continue
        predicted = np.asarray([score_ranks[index] for index in indices])
        actual = np.asarray(
            [float(rows[index][LABEL_RANK]) for index in indices]
        )
        if np.std(predicted) <= 0.0 or np.std(actual) <= 0.0:
            continue
        values.append(float(np.corrcoef(predicted, actual)[0, 1]))
    return {
        "dates": len(values),
        "mean_spearman": None if not values else float(np.mean(values)),
        "median_spearman": None if not values else float(np.median(values)),
        "positive_date_fraction": (
            None
            if not values
            else float(np.mean(np.asarray(values) > 0.0))
        ),
    }


def _trade_metrics(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not rows:
        return {
            "signals": 0,
            "dates": 0,
            "mean_net_return_pct": None,
            "median_net_return_pct": None,
            "hit_rate": None,
            "fifth_percentile_net_pct": None,
            "worst_net_return_pct": None,
        }
    values = np.asarray([float(row[LABEL_RETURN]) for row in rows])
    return {
        "signals": len(rows),
        "dates": len({str(row["market_date"]) for row in rows}),
        "mean_net_return_pct": float(np.mean(values)),
        "median_net_return_pct": float(np.median(values)),
        "hit_rate": float(np.mean(values > 0.0)),
        "fifth_percentile_net_pct": float(np.percentile(values, 5.0)),
        "worst_net_return_pct": float(np.min(values)),
    }


def _portfolio_metrics(
    rows: Sequence[Mapping[str, Any]],
    *,
    horizon_sessions: int,
    weighting: str,
) -> dict[str, Any]:
    """Simulate overlapping cohorts with idle cash and exact daily paths."""
    if weighting not in {"equal", "inverse_atr"}:
        raise ValueError("weighting must be equal or inverse_atr")
    if not rows:
        return {
            "daily_observations": 0,
            "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "annualized_sharpe": None,
        }
    cohorts: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        cohorts[str(row["market_date"])].append(row)
    daily: dict[str, float] = defaultdict(float)
    for cohort in cohorts.values():
        if weighting == "equal":
            raw_weights = np.ones(len(cohort), dtype=float)
        else:
            raw_weights = np.asarray(
                [
                    1.0 / max(float(row["x5_atr_14_pct"]), 0.10)
                    for row in cohort
                ]
            )
        weights = raw_weights / np.sum(raw_weights)
        for row, name_weight in zip(cohort, weights):
            path = row.get("label_5d_mark_to_market_path") or []
            if len(path) != horizon_sessions:
                raise ValueError("selected row has incomplete holding path")
            previous = 0.0
            for path_index, point in enumerate(path):
                gross = float(point["gross_return_from_entry_pct"])
                increment = gross - previous
                if path_index == horizon_sessions - 1:
                    increment -= float(row["round_trip_cost_pct"])
                daily[str(point["market_date"])] += (
                    increment
                    * float(name_weight)
                    / float(horizon_sessions)
                )
                previous = gross
    equity = peak = 1.0
    worst = 0.0
    daily_values = []
    for market_date in sorted(daily):
        value = float(daily[market_date])
        daily_values.append(value)
        equity *= 1.0 + value / 100.0
        peak = max(peak, equity)
        worst = min(worst, (equity / peak - 1.0) * 100.0)
    vector = np.asarray(daily_values)
    sharpe = (
        None
        if len(vector) < 2 or np.std(vector, ddof=1) <= 0.0
        else float(np.mean(vector) / np.std(vector, ddof=1) * np.sqrt(252.0))
    )
    return {
        "daily_observations": len(vector),
        "total_return_pct": float((equity - 1.0) * 100.0),
        "max_drawdown_pct": float(worst),
        "annualized_sharpe": sharpe,
        "weighting": weighting,
        "cohort_allocation_fraction": 1.0 / float(horizon_sessions),
    }


def evaluate_predictions(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    *,
    top_quantile: float,
    maximum_names: int,
    horizon_sessions: int,
    weighting: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    top_indices, diagnostics = selected_indices(
        rows,
        scores,
        top_quantile=top_quantile,
        maximum_names=maximum_names,
    )
    bottom_indices, bottom_diagnostics = selected_indices(
        rows,
        scores,
        top_quantile=top_quantile,
        maximum_names=maximum_names,
        highest=False,
    )
    score_ranks = date_local_score_percentiles(rows, scores)
    selected = []
    for index in top_indices:
        item = dict(rows[index])
        item["model_score"] = float(scores[index])
        item["model_score_cross_sectional_percentile"] = float(
            score_ranks[index]
        )
        selected.append(item)
    top_rows = [rows[index] for index in top_indices]
    bottom_rows = [rows[index] for index in bottom_indices]
    top = _trade_metrics(top_rows)
    bottom = _trade_metrics(bottom_rows)
    return (
        {
            "rank_information_coefficient": _rank_ic(rows, scores),
            "top_basket": top,
            "bottom_control": bottom,
            "top_minus_bottom_mean_net_pct": (
                None
                if top["mean_net_return_pct"] is None
                or bottom["mean_net_return_pct"] is None
                else float(
                    top["mean_net_return_pct"]
                    - bottom["mean_net_return_pct"]
                )
            ),
            "long_only_portfolio": _portfolio_metrics(
                top_rows,
                horizon_sessions=horizon_sessions,
                weighting=weighting,
            ),
            "selection_diagnostics": diagnostics,
            "bottom_selection_diagnostics": bottom_diagnostics,
        },
        selected,
    )


def promotion_gate(metrics: Mapping[str, Any]) -> tuple[bool, list[str]]:
    top = metrics["top_basket"]
    rank_ic = metrics["rank_information_coefficient"]
    portfolio = metrics["long_only_portfolio"]
    requirements = (
        ("minimum_100_signals", int(top["signals"]) >= 100),
        ("minimum_20_dates", int(top["dates"]) >= 20),
        (
            "positive_mean_return",
            top["mean_net_return_pct"] is not None
            and float(top["mean_net_return_pct"]) > 0.0,
        ),
        (
            "positive_median_return",
            top["median_net_return_pct"] is not None
            and float(top["median_net_return_pct"]) > 0.0,
        ),
        (
            "hit_rate_at_least_50pct",
            top["hit_rate"] is not None and float(top["hit_rate"]) >= 0.50,
        ),
        (
            "positive_rank_ic",
            rank_ic["mean_spearman"] is not None
            and float(rank_ic["mean_spearman"]) >= 0.01,
        ),
        (
            "positive_top_minus_bottom",
            metrics["top_minus_bottom_mean_net_pct"] is not None
            and float(metrics["top_minus_bottom_mean_net_pct"]) > 0.0,
        ),
        (
            "drawdown_above_minus_20pct",
            float(portfolio["max_drawdown_pct"]) > -20.0,
        ),
    )
    failures = [name for name, passed in requirements if not passed]
    return not failures, failures


def build_daily_snapshot(
    daily: Mapping[str, list[dict[str, Any]]],
    candidates: Sequence[str],
    *,
    as_of_date: str | None,
    minimum_cross_sectional_coverage: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build a label-free daily feature snapshot from completed candles."""
    if "QQQ" not in daily or "SPY" not in daily:
        raise ValueError("QQQ and SPY context histories are required")
    qqq_dates = {str(row["market_date"]) for row in daily["QQQ"]}
    spy_dates = {str(row["market_date"]) for row in daily["SPY"]}
    available_dates = sorted(
        value
        for value in qqq_dates & spy_dates
        if as_of_date is None or value <= as_of_date
    )
    if not available_dates:
        raise ValueError("no completed common QQQ/SPY decision date")
    decision_date = available_dates[-1]
    rows: list[dict[str, Any]] = []
    missing = []
    for symbol in candidates:
        candles = daily.get(symbol) or []
        positions = {
            str(row["market_date"]): index
            for index, row in enumerate(candles)
        }
        index = positions.get(decision_date)
        if index is None or index < 59:
            missing.append(symbol)
            continue
        features = technical_features(
            candles[max(0, index + 1 - 90) : index + 1]
        )
        eligible, failures = eligibility(features)
        rows.append(
            {
                "symbol": symbol,
                "market_date": decision_date,
                **features,
                "x5_eligible": eligible,
                "x5_eligibility_failures": failures,
                "feature_available_at": f"{decision_date} regular close",
                "research_only": True,
                "execution_enabled": False,
            }
        )
    required = max(
        2,
        int(
            len(candidates) * minimum_cross_sectional_coverage
            + 0.999999
        ),
    )
    if len(rows) < required:
        raise ValueError(
            f"snapshot coverage {len(rows)}/{len(candidates)} below {required}"
        )
    add_feature_ranks(rows)
    rows.sort(key=lambda row: str(row["symbol"]))
    return rows, {
        "decision_date": decision_date,
        "candidate_count": len(candidates),
        "available_count": len(rows),
        "coverage_fraction": len(rows) / len(candidates),
        "missing_symbols": sorted(missing),
    }
