from __future__ import annotations

"""Leakage-safe rolling descriptors for publicly observable call activity."""

import math
from statistics import median
from typing import Any, Iterable, Mapping


def number(value: Any) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def unusual_call_features(rows: Iterable[Mapping[str, Any]], lookback: int = 20, minimum_history: int = 10) -> list[dict[str, Any]]:
    """Add call-volume features using strictly earlier snapshots for each symbol."""
    history: dict[str, list[float]] = {}
    output = []
    for row in sorted(rows, key=lambda item: (str(item.get("symbol") or ""), str(item.get("market_date") or ""))):
        symbol = str(row.get("symbol") or "").upper()
        volume = number(row.get("option_call_volume"))
        open_interest = number(row.get("option_call_open_interest"))
        prior = history.setdefault(symbol, [])[-lookback:]
        features: dict[str, Any] = {"symbol": symbol, "market_date": str(row.get("market_date") or ""), "call_activity_history_count": len(prior)}
        if volume is not None and len(prior) >= minimum_history:
            prior_mean = sum(prior) / len(prior)
            prior_median = median(prior)
            variance = sum((item - prior_mean) ** 2 for item in prior) / len(prior)
            features.update({
                "call_volume_vs_prior_median": volume / prior_median if prior_median > 0 else None,
                "call_volume_zscore": (volume - prior_mean) / math.sqrt(variance) if variance > 0 else None,
                "call_volume_unusual": bool(variance > 0 and (volume - prior_mean) / math.sqrt(variance) >= 3.0),
            })
        else:
            features.update({"call_volume_vs_prior_median": None, "call_volume_zscore": None, "call_volume_unusual": False})
        features["call_volume_open_interest_ratio"] = volume / open_interest if volume is not None and open_interest and open_interest > 0 else None
        output.append(features)
        if volume is not None and volume >= 0:
            history[symbol].append(volume)
    return output
