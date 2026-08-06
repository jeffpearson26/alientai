from __future__ import annotations

"""Point-in-time features for a five-session cross-sectional stock picker."""

from collections import defaultdict
from typing import Any, Mapping, Sequence

import numpy as np


RANK_FEATURES = (
    "x5_return_1d_pct",
    "x5_return_5d_pct",
    "x5_return_10d_pct",
    "x5_roc_10d_pct",
    "x5_rsi_14",
    "x5_stochastic_k_14",
    "x5_stochastic_d_3",
    "x5_cci_20",
    "x5_atr_14_pct",
    "x5_bollinger_pct_b_20",
    "x5_bollinger_width_20_pct",
    "x5_realized_volatility_10d_annualized_pct",
    "x5_realized_volatility_20d_annualized_pct",
    "x5_relative_volume_20d",
    "x5_volume_roc_5d_pct",
    "x5_up_down_volume_ratio_20d",
    "x5_distance_ema_10_pct",
    "x5_distance_ema_20_pct",
    "x5_macd_histogram_pct",
    "x5_adx_14",
    "x5_distance_from_5d_high_pct",
    "x5_distance_from_5d_low_pct",
    "x5_gap_1d_pct",
)

TRANSPARENT_WEIGHTS = {
    "rank_x5_return_5d_pct": 0.25,
    "rank_x5_return_10d_pct": 0.15,
    "rank_x5_roc_10d_pct": 0.15,
    "rank_x5_stochastic_k_14": 0.10,
    "rank_x5_cci_20": 0.10,
    "rank_x5_relative_volume_20d": 0.10,
    "rank_x5_bollinger_pct_b_20": 0.10,
    "rank_x5_distance_ema_10_pct": 0.05,
}


def _pct(current: float, prior: float) -> float:
    return (current / prior - 1.0) * 100.0


def _ema_series(values: np.ndarray, period: int) -> np.ndarray:
    if len(values) == 0:
        return np.asarray([], dtype=float)
    alpha = 2.0 / (period + 1.0)
    output = np.empty(len(values), dtype=float)
    output[0] = float(values[0])
    for index in range(1, len(values)):
        output[index] = (
            alpha * float(values[index])
            + (1.0 - alpha) * output[index - 1]
        )
    return output


def _rsi(values: np.ndarray, period: int) -> float:
    changes = np.diff(values)
    gains = np.maximum(changes, 0.0)
    losses = np.maximum(-changes, 0.0)
    average_gain = float(np.mean(gains[:period]))
    average_loss = float(np.mean(losses[:period]))
    for index in range(period, len(changes)):
        average_gain = (
            average_gain * (period - 1) + float(gains[index])
        ) / period
        average_loss = (
            average_loss * (period - 1) + float(losses[index])
        ) / period
    if average_loss == 0.0:
        return 100.0 if average_gain > 0.0 else 50.0
    return 100.0 - 100.0 / (1.0 + average_gain / average_loss)


def _true_ranges(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray
) -> np.ndarray:
    prior_close = closes[:-1]
    return np.maximum.reduce(
        (
            highs[1:] - lows[1:],
            np.abs(highs[1:] - prior_close),
            np.abs(lows[1:] - prior_close),
        )
    )


def _adx(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int
) -> float | None:
    if len(closes) < period * 2 + 1:
        return None
    up = np.diff(highs)
    down = -np.diff(lows)
    plus_dm = np.where((up > down) & (up > 0.0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0.0), down, 0.0)
    tr = _true_ranges(highs, lows, closes)
    atr = float(np.sum(tr[:period]))
    plus = float(np.sum(plus_dm[:period]))
    minus = float(np.sum(minus_dm[:period]))
    dx_values: list[float] = []
    for index in range(period, len(tr)):
        atr = atr - atr / period + float(tr[index])
        plus = plus - plus / period + float(plus_dm[index])
        minus = minus - minus / period + float(minus_dm[index])
        if atr <= 0.0:
            continue
        plus_di = 100.0 * plus / atr
        minus_di = 100.0 * minus / atr
        denominator = plus_di + minus_di
        dx_values.append(
            0.0
            if denominator <= 0.0
            else 100.0 * abs(plus_di - minus_di) / denominator
        )
    if len(dx_values) < period:
        return None
    adx = float(np.mean(dx_values[:period]))
    for value in dx_values[period:]:
        adx = (adx * (period - 1) + float(value)) / period
    return adx


def _stochastic_k(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    end_index: int,
    period: int,
) -> float:
    start = end_index + 1 - period
    highest = float(np.max(highs[start : end_index + 1]))
    lowest = float(np.min(lows[start : end_index + 1]))
    if highest <= lowest:
        return 50.0
    return float((closes[end_index] - lowest) / (highest - lowest) * 100.0)


def technical_features(
    candles: Sequence[Mapping[str, Any]],
) -> dict[str, float | None]:
    """Build features from candles ending at the decision close only."""
    if len(candles) < 60:
        raise ValueError("five-session technical features require 60 candles")
    closes = np.asarray([float(row["close"]) for row in candles], dtype=float)
    opens = np.asarray([float(row["open"]) for row in candles], dtype=float)
    highs = np.asarray([float(row["high"]) for row in candles], dtype=float)
    lows = np.asarray([float(row["low"]) for row in candles], dtype=float)
    volumes = np.asarray([float(row["volume"]) for row in candles], dtype=float)
    if (
        np.any(closes <= 0.0)
        or np.any(opens <= 0.0)
        or np.any(highs <= 0.0)
        or np.any(lows <= 0.0)
        or np.any(volumes < 0.0)
    ):
        raise ValueError("invalid OHLCV values")

    log_returns = np.diff(np.log(closes))
    true_ranges = _true_ranges(highs, lows, closes)
    atr_14 = float(np.mean(true_ranges[-14:]))
    typical = (highs[-20:] + lows[-20:] + closes[-20:]) / 3.0
    typical_mean = float(np.mean(typical))
    mean_deviation = float(np.mean(np.abs(typical - typical_mean)))
    cci = (
        0.0
        if mean_deviation == 0.0
        else float((typical[-1] - typical_mean) / (0.015 * mean_deviation))
    )

    middle = float(np.mean(closes[-20:]))
    deviation = float(np.std(closes[-20:], ddof=0))
    lower = middle - 2.0 * deviation
    upper = middle + 2.0 * deviation
    band_range = upper - lower

    stochastic_values = [
        _stochastic_k(highs, lows, closes, index, 14)
        for index in range(len(closes) - 3, len(closes))
    ]
    ema_10 = _ema_series(closes, 10)
    ema_20 = _ema_series(closes, 20)
    ema_12 = _ema_series(closes, 12)
    ema_26 = _ema_series(closes, 26)
    macd = ema_12 - ema_26
    signal = _ema_series(macd, 9)

    directions = np.sign(np.diff(closes[-21:]))
    directional_volume = volumes[-20:]
    up_volume = float(np.sum(directional_volume[directions > 0.0]))
    down_volume = float(np.sum(directional_volume[directions < 0.0]))
    average_prior_volume = float(np.mean(volumes[-21:-1]))
    average_dollar_volume = float(np.mean(closes[-20:] * volumes[-20:]))
    high_5 = float(np.max(highs[-5:]))
    low_5 = float(np.min(lows[-5:]))

    return {
        "x5_return_1d_pct": _pct(closes[-1], closes[-2]),
        "x5_return_5d_pct": _pct(closes[-1], closes[-6]),
        "x5_return_10d_pct": _pct(closes[-1], closes[-11]),
        # The supplied thesis includes both names even though they are
        # algebraically identical; the report makes that redundancy explicit.
        "x5_roc_10d_pct": _pct(closes[-1], closes[-11]),
        "x5_rsi_14": _rsi(closes[-40:], 14),
        "x5_stochastic_k_14": stochastic_values[-1],
        "x5_stochastic_d_3": float(np.mean(stochastic_values)),
        "x5_cci_20": cci,
        "x5_atr_14_pct": atr_14 / closes[-1] * 100.0,
        "x5_bollinger_pct_b_20": (
            0.5 if band_range <= 0.0 else (closes[-1] - lower) / band_range
        ),
        "x5_bollinger_width_20_pct": (
            0.0 if middle <= 0.0 else band_range / middle * 100.0
        ),
        "x5_realized_volatility_10d_annualized_pct": float(
            np.std(log_returns[-10:], ddof=0) * np.sqrt(252.0) * 100.0
        ),
        "x5_realized_volatility_20d_annualized_pct": float(
            np.std(log_returns[-20:], ddof=0) * np.sqrt(252.0) * 100.0
        ),
        "x5_relative_volume_20d": (
            None
            if average_prior_volume <= 0.0
            else float(volumes[-1] / average_prior_volume)
        ),
        "x5_volume_roc_5d_pct": (
            None
            if volumes[-6] <= 0.0
            else _pct(volumes[-1], volumes[-6])
        ),
        "x5_up_down_volume_ratio_20d": (
            up_volume / down_volume
            if down_volume > 0.0
            else (up_volume if up_volume > 0.0 else 1.0)
        ),
        "x5_distance_ema_10_pct": _pct(closes[-1], ema_10[-1]),
        "x5_distance_ema_20_pct": _pct(closes[-1], ema_20[-1]),
        "x5_macd_histogram_pct": (
            float((macd[-1] - signal[-1]) / closes[-1] * 100.0)
        ),
        "x5_adx_14": _adx(highs, lows, closes, 14),
        "x5_distance_from_5d_high_pct": _pct(closes[-1], high_5),
        "x5_distance_from_5d_low_pct": _pct(closes[-1], low_5),
        "x5_gap_1d_pct": _pct(opens[-1], closes[-2]),
        "x5_average_dollar_volume_20d": average_dollar_volume,
        "x5_decision_price": float(closes[-1]),
    }


def percentile_ranks(values: np.ndarray) -> np.ndarray:
    """Return stable 0..1 average-tie ranks while retaining missing values."""
    output = np.full(len(values), np.nan, dtype=float)
    finite = np.flatnonzero(np.isfinite(values))
    if len(finite) == 1:
        output[finite[0]] = 0.5
        return output
    if len(finite) == 0:
        return output
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
        output[ordered[start:end]] = float(np.mean(positions[start:end]))
        start = end
    return output


def add_date_local_ranks(rows: Sequence[dict[str, Any]]) -> None:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_date[str(row["market_date"])].append(row)
    for group in by_date.values():
        for feature in RANK_FEATURES:
            values = np.asarray(
                [
                    float(row[feature])
                    if row.get(feature) is not None
                    and np.isfinite(float(row[feature]))
                    else np.nan
                    for row in group
                ],
                dtype=float,
            )
            ranks = percentile_ranks(values)
            for row, rank in zip(group, ranks):
                row[f"rank_{feature}"] = (
                    None if not np.isfinite(rank) else float(rank)
                )
        target_values = np.asarray(
            [float(row["label_5d_net_return_pct"]) for row in group],
            dtype=float,
        )
        target_ranks = percentile_ranks(target_values)
        for row, target_rank in zip(group, target_ranks):
            row["label_5d_cross_sectional_return_rank"] = float(target_rank)
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


def eligibility(
    features: Mapping[str, Any],
    *,
    minimum_price: float = 5.0,
    minimum_average_dollar_volume: float = 20_000_000.0,
    maximum_atr_pct: float = 10.0,
    minimum_adx: float = 15.0,
    maximum_absolute_gap_pct: float = 10.0,
) -> tuple[bool, list[str]]:
    failures = []
    checks = (
        ("price", float(features["x5_decision_price"]) >= minimum_price),
        (
            "liquidity",
            float(features["x5_average_dollar_volume_20d"])
            >= minimum_average_dollar_volume,
        ),
        ("atr_cap", float(features["x5_atr_14_pct"]) <= maximum_atr_pct),
        (
            "adx",
            features.get("x5_adx_14") is not None
            and float(features["x5_adx_14"]) >= minimum_adx,
        ),
        (
            "gap_cap",
            abs(float(features["x5_gap_1d_pct"]))
            <= maximum_absolute_gap_pct,
        ),
    )
    for name, passed in checks:
        if not passed:
            failures.append(name)
    return not failures, failures
