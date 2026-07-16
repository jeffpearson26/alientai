from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def pct_change(start: float, end: float) -> float:
    if start <= 0:
        return 0.0
    return ((end - start) / start) * 100.0


def candle_close(candle: Dict[str, Any]) -> float:
    return safe_float(candle.get("close"), 0.0)


def candle_open(candle: Dict[str, Any]) -> float:
    return safe_float(candle.get("open"), 0.0)


def candle_high(candle: Dict[str, Any]) -> float:
    return safe_float(candle.get("high"), 0.0)


def candle_low(candle: Dict[str, Any]) -> float:
    return safe_float(candle.get("low"), 0.0)


def candle_volume(candle: Dict[str, Any]) -> float:
    return safe_float(candle.get("volume"), 0.0)


def build_pattern_features(candles: List[Dict[str, Any]], window: int = 12) -> Optional[Dict[str, float]]:
    """
    Builds a simple fingerprint from the latest N candles.

    V1 features:
    - total return over the window
    - first-half return
    - second-half return
    - high/low range percent
    - close position inside the window range
    - average candle body percent
    - average volume relative to previous candles if available
    """

    if not candles or len(candles) < window:
        return None

    recent = candles[-window:]

    first = recent[0]
    last = recent[-1]

    first_open = candle_open(first)
    last_close = candle_close(last)

    if first_open <= 0 or last_close <= 0:
        return None

    highs = [candle_high(c) for c in recent if candle_high(c) > 0]
    lows = [candle_low(c) for c in recent if candle_low(c) > 0]
    closes = [candle_close(c) for c in recent if candle_close(c) > 0]

    if not highs or not lows or not closes:
        return None

    high = max(highs)
    low = min(lows)

    if low <= 0:
        return None

    mid_index = max(1, window // 2)

    first_half_start = candle_open(recent[0])
    first_half_end = candle_close(recent[mid_index - 1])
    second_half_start = candle_open(recent[mid_index])
    second_half_end = candle_close(recent[-1])

    body_pcts = []

    for c in recent:
        o = candle_open(c)
        cl = candle_close(c)

        if o > 0:
            body_pcts.append(abs(pct_change(o, cl)))

    avg_body_pct = sum(body_pcts) / len(body_pcts) if body_pcts else 0.0

    range_pct = pct_change(low, high)

    if high > low:
        close_position = ((last_close - low) / (high - low)) * 100.0
    else:
        close_position = 50.0

    recent_volume = sum(candle_volume(c) for c in recent) / float(window)

    prior = candles[-(window * 3):-window] if len(candles) >= window * 3 else candles[:-window]
    prior_volumes = [candle_volume(c) for c in prior if candle_volume(c) > 0]

    if prior_volumes:
        prior_avg_volume = sum(prior_volumes) / len(prior_volumes)
        relative_volume = recent_volume / prior_avg_volume if prior_avg_volume > 0 else 1.0
    else:
        relative_volume = 1.0

    return {
        "window_return_pct": pct_change(first_open, last_close),
        "first_half_return_pct": pct_change(first_half_start, first_half_end),
        "second_half_return_pct": pct_change(second_half_start, second_half_end),
        "range_pct": range_pct,
        "close_position_pct": close_position,
        "avg_body_pct": avg_body_pct,
        "relative_volume": relative_volume,
    }


def feature_distance(a: Dict[str, float], b: Dict[str, float]) -> float:
    """
    Weighted Euclidean distance.

    Lower distance = more similar.
    We normalize some features by rough natural scales so one feature does not dominate.
    """

    weights = {
        "window_return_pct": 1.00,
        "first_half_return_pct": 0.70,
        "second_half_return_pct": 0.90,
        "range_pct": 0.55,
        "close_position_pct": 0.035,
        "avg_body_pct": 0.60,
        "relative_volume": 0.80,
    }

    scale = {
        "window_return_pct": 5.0,
        "first_half_return_pct": 4.0,
        "second_half_return_pct": 4.0,
        "range_pct": 8.0,
        "close_position_pct": 100.0,
        "avg_body_pct": 3.0,
        "relative_volume": 3.0,
    }

    total = 0.0

    for key, weight in weights.items():
        av = float(a.get(key, 0.0))
        bv = float(b.get(key, 0.0))
        s = float(scale.get(key, 1.0)) or 1.0

        diff = (av - bv) / s
        total += weight * diff * diff

    return math.sqrt(total)


def forward_outcome(
    candles: List[Dict[str, Any]],
    start_index: int,
    *,
    horizon_bars: int = 78,
) -> Optional[Dict[str, float]]:
    """
    Measures what happened after a historical pattern.

    For 5-minute regular-session candles, 78 bars ~= one trading day.
    With extended hours included, 78 bars is still a reasonable initial horizon
    for V1 scoring, but later we can build session-aware horizons.
    """

    entry_index = start_index

    if entry_index < 0 or entry_index >= len(candles) - 2:
        return None

    end_index = min(len(candles) - 1, entry_index + horizon_bars)

    if end_index <= entry_index:
        return None

    entry_close = candle_close(candles[entry_index])

    if entry_close <= 0:
        return None

    future = candles[entry_index + 1:end_index + 1]

    if not future:
        return None

    future_closes = [candle_close(c) for c in future if candle_close(c) > 0]
    future_highs = [candle_high(c) for c in future if candle_high(c) > 0]
    future_lows = [candle_low(c) for c in future if candle_low(c) > 0]

    if not future_closes or not future_highs or not future_lows:
        return None

    final_close = future_closes[-1]
    max_high = max(future_highs)
    min_low = min(future_lows)

    final_return_pct = pct_change(entry_close, final_close)
    max_gain_pct = pct_change(entry_close, max_high)
    max_drawdown_pct = pct_change(entry_close, min_low)

    return {
        "forward_return_pct": final_return_pct,
        "max_gain_pct": max_gain_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "win": 1.0 if final_return_pct > 0 else 0.0,
    }


def summarize_similar_outcomes(outcomes: List[Dict[str, float]]) -> Dict[str, float]:
    if not outcomes:
        return {
            "cases": 0,
            "win_rate_pct": 0.0,
            "avg_forward_return_pct": 0.0,
            "avg_max_gain_pct": 0.0,
            "avg_max_drawdown_pct": 0.0,
        }

    cases = len(outcomes)
    wins = sum(1 for o in outcomes if safe_float(o.get("win"), 0.0) > 0.0)

    return {
        "cases": float(cases),
        "win_rate_pct": (wins / cases) * 100.0,
        "avg_forward_return_pct": sum(safe_float(o.get("forward_return_pct"), 0.0) for o in outcomes) / cases,
        "avg_max_gain_pct": sum(safe_float(o.get("max_gain_pct"), 0.0) for o in outcomes) / cases,
        "avg_max_drawdown_pct": sum(safe_float(o.get("max_drawdown_pct"), 0.0) for o in outcomes) / cases,
    }
