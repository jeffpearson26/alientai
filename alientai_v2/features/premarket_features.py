from __future__ import annotations

"""Leakage-safe features from Alpha Vantage extended-hours five-minute candles."""

from datetime import datetime, time
from statistics import median
from typing import Any, Dict, Iterable, List, Mapping, Optional


PREMARKET_START = time(4, 0)
PREMARKET_CUTOFF = time(9, 25)
REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)


def number(value: Any) -> Optional[float]:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def parse_timestamp(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


def pct_change(new: Optional[float], old: Optional[float]) -> Optional[float]:
    if new is None or old is None or old == 0:
        return None
    return (new / old - 1.0) * 100.0


def _dated_rows(rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for source in rows:
        stamp = parse_timestamp(source.get("timestamp"))
        if stamp is None:
            continue
        row = dict(source)
        row["_stamp"] = stamp
        for field in ("open", "high", "low", "close", "volume"):
            row[field] = number(row.get(field))
        output.append(row)
    return sorted(output, key=lambda row: row["_stamp"])


def build_premarket_features(
    rows: Iterable[Mapping[str, Any]], market_date: str, cutoff: time = PREMARKET_CUTOFF,
) -> Dict[str, Any]:
    dated = _dated_rows(rows)
    try:
        event_day = datetime.strptime(market_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("market_date must use YYYY-MM-DD")

    premarket = [
        row for row in dated
        if row["_stamp"].date() == event_day and PREMARKET_START <= row["_stamp"].time() <= cutoff
    ]
    previous_regular = [
        row for row in dated
        if row["_stamp"].date() < event_day and REGULAR_OPEN <= row["_stamp"].time() <= REGULAR_CLOSE
    ]
    previous_close = previous_regular[-1].get("close") if previous_regular else None
    valid = [row for row in premarket if row.get("close") is not None]
    base: Dict[str, Any] = {
        "premarket_available": bool(valid),
        "premarket_previous_close_available": previous_close is not None,
        "premarket_bar_count": len(valid),
        "premarket_cutoff_et": cutoff.strftime("%H:%M"),
    }
    if not valid:
        return base

    first_close = valid[0]["close"]
    last_close = valid[-1]["close"]
    highs = [row["high"] for row in valid if row.get("high") is not None]
    lows = [row["low"] for row in valid if row.get("low") is not None]
    volumes = [max(0.0, row.get("volume") or 0.0) for row in valid]
    total_volume = sum(volumes)
    dollar_volume = sum((row.get("close") or 0.0) * volume for row, volume in zip(valid, volumes))
    vwap = dollar_volume / total_volume if total_volume else None

    cutoff_30 = datetime.combine(event_day, cutoff).timestamp() - 30 * 60
    cutoff_60 = datetime.combine(event_day, cutoff).timestamp() - 60 * 60

    def close_at_or_before(epoch: float) -> Optional[float]:
        candidates = [row["close"] for row in valid if row["_stamp"].timestamp() <= epoch]
        return candidates[-1] if candidates else None

    prior_totals = []
    for prior_day in sorted({row["_stamp"].date() for row in dated if row["_stamp"].date() < event_day})[-10:]:
        volume = sum(
            max(0.0, row.get("volume") or 0.0) for row in dated
            if row["_stamp"].date() == prior_day and PREMARKET_START <= row["_stamp"].time() <= cutoff
        )
        if volume > 0:
            prior_totals.append(volume)
    typical_volume = median(prior_totals) if prior_totals else None
    relative_volume = total_volume / typical_volume if typical_volume else None
    high = max(highs) if highs else None
    low = min(lows) if lows else None
    base.update({
        "premarket_first_close": first_close,
        "premarket_last_close": last_close,
        "premarket_previous_regular_close": previous_close,
        "premarket_gap_pct": pct_change(last_close, previous_close),
        "premarket_session_return_pct": pct_change(last_close, first_close),
        "premarket_high_vs_previous_close_pct": pct_change(high, previous_close),
        "premarket_low_vs_previous_close_pct": pct_change(low, previous_close),
        "premarket_range_pct": pct_change(high, low),
        "premarket_return_30m_pct": pct_change(last_close, close_at_or_before(cutoff_30)),
        "premarket_return_60m_pct": pct_change(last_close, close_at_or_before(cutoff_60)),
        "premarket_volume": total_volume,
        "premarket_typical_prior_volume": typical_volume,
        "premarket_relative_volume": relative_volume,
        "premarket_dollar_volume": dollar_volume,
        "premarket_vwap": vwap,
        "premarket_last_vs_vwap_pct": pct_change(last_close, vwap),
        "premarket_last_timestamp_et": valid[-1]["_stamp"].strftime("%Y-%m-%d %H:%M:%S"),
    })
    return base
