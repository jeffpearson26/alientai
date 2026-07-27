from __future__ import annotations

"""Point-in-time features for a multi-horizon trend/pullback model."""

import math
from typing import Any, Mapping, Sequence

import numpy as np


HORIZONS = (20, 63, 126)


def _positive_prices(candles: Sequence[Mapping[str, Any]]) -> np.ndarray:
    values = []
    for candle in candles:
        try:
            value = float(candle.get("close"))
        except (TypeError, ValueError):
            raise ValueError("every candle requires a numeric close")
        if not math.isfinite(value) or value <= 0:
            raise ValueError("close prices must be finite and positive")
        values.append(value)
    return np.asarray(values, dtype=float)


def log_slope_pct_per_day(prices: Sequence[float]) -> float:
    values = np.asarray(prices, dtype=float)
    if len(values) < 2 or np.any(~np.isfinite(values)) or np.any(values <= 0):
        raise ValueError("at least two finite positive prices are required")
    x = np.arange(len(values), dtype=float)
    slope = float(np.polyfit(x, np.log(values), 1)[0])
    return (math.exp(slope) - 1.0) * 100.0


def pct_change(new: float, old: float) -> float:
    return (new / old - 1.0) * 100.0


def build_pullback_features(candles: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Build features using only candles at or before the decision close."""
    if len(candles) < max(HORIZONS):
        raise ValueError("at least 126 completed daily candles are required")
    closes = _positive_prices(candles)
    latest = float(closes[-1])
    result: dict[str, Any] = {}
    slopes = {}
    for horizon in HORIZONS:
        window = closes[-horizon:]
        slopes[horizon] = log_slope_pct_per_day(window)
        mean = float(np.mean(window))
        result[f"pullback_trend_slope_{horizon}d_pct_per_day"] = slopes[horizon]
        result[f"pullback_distance_from_sma_{horizon}d_pct"] = pct_change(latest, mean)

    for horizon in (5, 10, 20):
        window = closes[-horizon:]
        result[f"pullback_from_{horizon}d_high_pct"] = pct_change(
            latest, float(np.max(window))
        )
    result.update({
        "pullback_return_1d_pct": pct_change(latest, float(closes[-2])),
        "pullback_return_5d_pct": pct_change(latest, float(closes[-6])),
        "pullback_volatility_20d_pct": float(
            np.std(np.diff(np.log(closes[-21:])), ddof=1) * 100.0
        ),
        "pullback_all_trend_slopes_positive": all(value > 0.0 for value in slopes.values()),
    })
    result["pullback_setup_eligible"] = bool(
        result["pullback_all_trend_slopes_positive"]
        and result["pullback_distance_from_sma_126d_pct"] > 0.0
        and -12.0 <= result["pullback_from_20d_high_pct"] <= -1.0
        and result["pullback_return_5d_pct"] < 0.0
    )
    return result
