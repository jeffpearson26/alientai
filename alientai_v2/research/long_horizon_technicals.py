from __future__ import annotations

"""Comprehensive point-in-time daily technicals for long-horizon research."""

from typing import Any, Mapping, Sequence

import numpy as np

from alientai_v2.features.technical_snapshot import build_technical_snapshot


RETURN_WINDOWS = (1, 5, 10, 20, 40, 60, 90, 126, 189, 252)
TREND_WINDOWS = (20, 50, 60, 100, 126, 200, 252)
VOLATILITY_WINDOWS = (5, 10, 20, 60, 126, 252)
RANGE_WINDOWS = (20, 55, 126, 252)


def _return(current: float, prior: float) -> float:
    return (current / prior - 1.0) * 100.0


def _ema(values: np.ndarray, period: int) -> float:
    alpha = 2.0 / (period + 1.0)
    result = float(values[0])
    for value in values[1:]:
        result = alpha * float(value) + (1.0 - alpha) * result
    return result


def _rsi(values: np.ndarray, period: int) -> float | None:
    if len(values) <= period:
        return None
    changes = np.diff(values[-(period + 1) :])
    gains = float(np.mean(np.maximum(changes, 0.0)))
    losses = float(np.mean(np.maximum(-changes, 0.0)))
    if losses == 0.0:
        return 100.0 if gains > 0.0 else 50.0
    return 100.0 - 100.0 / (1.0 + gains / losses)


def _slope(values: np.ndarray) -> tuple[float | None, float | None]:
    if len(values) < 3 or np.any(values <= 0):
        return None, None
    x = np.arange(len(values), dtype=float)
    y = np.log(values.astype(float))
    coefficient = np.polyfit(x, y, 1)
    fitted = np.polyval(coefficient, x)
    residual = float(np.sum((y - fitted) ** 2))
    total = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - residual / total if total > 0.0 else 0.0
    return float((np.exp(coefficient[0]) - 1.0) * 100.0), r_squared


def _max_drawdown(values: np.ndarray) -> float:
    peak = np.maximum.accumulate(values)
    return float(np.min(values / peak - 1.0) * 100.0)


def _skew(values: np.ndarray) -> float | None:
    if len(values) < 3:
        return None
    standard_deviation = float(np.std(values, ddof=0))
    if standard_deviation == 0.0:
        return 0.0
    return float(np.mean(((values - np.mean(values)) / standard_deviation) ** 3))


def _money_flow_index(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    period: int = 14,
) -> float | None:
    if len(closes) <= period:
        return None
    typical = (highs + lows + closes) / 3.0
    flow = typical * volumes
    changes = np.diff(typical[-(period + 1) :])
    recent_flow = flow[-period:]
    positive = float(np.sum(recent_flow[changes > 0.0]))
    negative = float(np.sum(recent_flow[changes < 0.0]))
    if negative == 0.0:
        return 100.0 if positive > 0.0 else 50.0
    return 100.0 - 100.0 / (1.0 + positive / negative)


def long_horizon_technical_features(
    candles: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if len(candles) < 126:
        raise ValueError("long-horizon technicals require at least 126 candles")
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
        raise ValueError("invalid candle values")
    daily_returns = np.diff(np.log(closes)) * 100.0
    output: dict[str, Any] = {
        **build_technical_snapshot(candles[-min(252, len(candles)) :]),
        "lh_gap_1d_pct": _return(opens[-1], closes[-2]),
        "lh_body_1d_pct": _return(closes[-1], opens[-1]),
        "lh_range_1d_pct": _return(highs[-1], lows[-1]),
        "lh_rsi_5": _rsi(closes, 5),
        "lh_rsi_28": _rsi(closes, 28),
        "lh_money_flow_index_14": _money_flow_index(
            highs, lows, closes, volumes
        ),
    }
    for window in RETURN_WINDOWS:
        output[f"lh_return_{window}d_pct"] = (
            _return(closes[-1], closes[-1 - window])
            if len(closes) > window
            else None
        )
    for window in TREND_WINDOWS:
        if len(closes) >= window:
            sample = closes[-window:]
            simple_average = float(np.mean(sample))
            exponential_average = _ema(sample, window)
            slope, r_squared = _slope(sample)
            output.update(
                {
                    f"lh_sma_{window}_distance_pct": _return(
                        closes[-1], simple_average
                    ),
                    f"lh_ema_{window}_distance_pct": _return(
                        closes[-1], exponential_average
                    ),
                    f"lh_slope_{window}_pct_per_day": slope,
                    f"lh_slope_{window}_r2": r_squared,
                    f"lh_above_sma_{window}": bool(
                        closes[-1] > simple_average
                    ),
                }
            )
        else:
            output.update(
                {
                    f"lh_sma_{window}_distance_pct": None,
                    f"lh_ema_{window}_distance_pct": None,
                    f"lh_slope_{window}_pct_per_day": None,
                    f"lh_slope_{window}_r2": None,
                    f"lh_above_sma_{window}": None,
                }
            )
    for window in VOLATILITY_WINDOWS:
        if len(daily_returns) >= window:
            sample = daily_returns[-window:]
            downside = sample[sample < 0.0]
            output.update(
                {
                    f"lh_realized_volatility_{window}d_pct": float(
                        np.std(sample, ddof=0)
                    ),
                    f"lh_downside_volatility_{window}d_pct": (
                        float(np.std(downside, ddof=0))
                        if len(downside) >= 2 else 0.0
                    ),
                    f"lh_return_skew_{window}d": _skew(sample),
                    f"lh_positive_fraction_{window}d": float(
                        np.mean(sample > 0.0)
                    ),
                }
            )
        else:
            output.update(
                {
                    f"lh_realized_volatility_{window}d_pct": None,
                    f"lh_downside_volatility_{window}d_pct": None,
                    f"lh_return_skew_{window}d": None,
                    f"lh_positive_fraction_{window}d": None,
                }
            )
    for window in RANGE_WINDOWS:
        if len(closes) >= window:
            sample_close = closes[-window:]
            sample_high = highs[-window:]
            sample_low = lows[-window:]
            highest = float(np.max(sample_high))
            lowest = float(np.min(sample_low))
            output.update(
                {
                    f"lh_distance_from_{window}d_high_pct": _return(
                        closes[-1], highest
                    ),
                    f"lh_distance_from_{window}d_low_pct": _return(
                        closes[-1], lowest
                    ),
                    f"lh_donchian_position_{window}d": (
                        float((closes[-1] - lowest) / (highest - lowest))
                        if highest > lowest
                        else 0.5
                    ),
                    f"lh_max_drawdown_{window}d_pct": _max_drawdown(
                        sample_close
                    ),
                    f"lh_breakout_{window}d": bool(
                        closes[-1] >= float(np.max(highs[-window:-1]))
                        if window > 1
                        else False
                    ),
                }
            )
        else:
            output.update(
                {
                    f"lh_distance_from_{window}d_high_pct": None,
                    f"lh_distance_from_{window}d_low_pct": None,
                    f"lh_donchian_position_{window}d": None,
                    f"lh_max_drawdown_{window}d_pct": None,
                    f"lh_breakout_{window}d": None,
                }
            )
    for window in (5, 20, 60, 126):
        if len(volumes) >= window:
            average = float(np.mean(volumes[-window:]))
            output[f"lh_latest_volume_vs_{window}d_mean"] = (
                float(volumes[-1] / average) if average > 0.0 else None
            )
        else:
            output[f"lh_latest_volume_vs_{window}d_mean"] = None
    for window in (20, 60, 126):
        if len(closes) > window:
            signs = np.sign(np.diff(closes[-(window + 1) :]))
            obv_change = float(np.sum(signs * volumes[-window:]))
            average_volume = float(np.mean(volumes[-window:]))
            output[f"lh_obv_change_{window}d_normalized"] = (
                obv_change / average_volume if average_volume > 0.0 else None
            )
        else:
            output[f"lh_obv_change_{window}d_normalized"] = None
    if len(closes) >= 20:
        typical = (highs[-20:] + lows[-20:] + closes[-20:]) / 3.0
        money_flow_multiplier = np.divide(
            2.0 * closes[-20:] - highs[-20:] - lows[-20:],
            highs[-20:] - lows[-20:],
            out=np.zeros(20, dtype=float),
            where=(highs[-20:] - lows[-20:]) != 0.0,
        )
        output["lh_chaikin_money_flow_20d"] = float(
            np.sum(money_flow_multiplier * volumes[-20:])
            / max(float(np.sum(volumes[-20:])), 1.0)
        )
        highest = float(np.max(highs[-14:]))
        lowest = float(np.min(lows[-14:]))
        output["lh_stochastic_k_14"] = (
            float((closes[-1] - lowest) / (highest - lowest) * 100.0)
            if highest > lowest
            else 50.0
        )
        output["lh_williams_r_14"] = output["lh_stochastic_k_14"] - 100.0
    return output
