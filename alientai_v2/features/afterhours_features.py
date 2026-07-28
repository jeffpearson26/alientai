from __future__ import annotations

"""Leakage-safe features for the session preceding a market date."""

from datetime import datetime, time
from statistics import median
from typing import Any, Dict, Iterable, Mapping

from alientai_v2.features.premarket_features import _dated_rows, pct_change


REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)
AFTERHOURS_START = time(16, 5)
AFTERHOURS_END = time(19, 55)


def build_afterhours_features(
    rows: Iterable[Mapping[str, Any]], market_date: str,
) -> Dict[str, Any]:
    """Describe the latest completed after-hours session before ``market_date``."""
    dated = _dated_rows(rows)
    try:
        event_day = datetime.strptime(market_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("market_date must use YYYY-MM-DD")

    prior_dates = sorted({
        row["_stamp"].date()
        for row in dated
        if row["_stamp"].date() < event_day
        and REGULAR_OPEN <= row["_stamp"].time() <= AFTERHOURS_END
    })
    base: Dict[str, Any] = {
        "afterhours_available": False,
        "afterhours_bar_count": 0,
    }
    if not prior_dates:
        return base

    session_day = prior_dates[-1]
    regular = [
        row for row in dated
        if row["_stamp"].date() == session_day
        and REGULAR_OPEN <= row["_stamp"].time() <= REGULAR_CLOSE
        and row.get("close") is not None
    ]
    afterhours = [
        row for row in dated
        if row["_stamp"].date() == session_day
        and AFTERHOURS_START <= row["_stamp"].time() <= AFTERHOURS_END
        and row.get("close") is not None
    ]
    base.update({
        "afterhours_session_date": session_day.isoformat(),
        "afterhours_bar_count": len(afterhours),
        "afterhours_previous_regular_close_available": bool(regular),
    })
    if not afterhours or not regular:
        return base

    previous_close = regular[-1]["close"]
    first_close = afterhours[0]["close"]
    last_close = afterhours[-1]["close"]
    total_volume = sum(max(0.0, row.get("volume") or 0.0) for row in afterhours)
    prior_totals = []
    for prior_day in prior_dates[:-1][-10:]:
        volume = sum(
            max(0.0, row.get("volume") or 0.0)
            for row in dated
            if row["_stamp"].date() == prior_day
            and AFTERHOURS_START <= row["_stamp"].time() <= AFTERHOURS_END
        )
        if volume > 0:
            prior_totals.append(volume)
    typical_volume = median(prior_totals) if prior_totals else None
    base.update({
        "afterhours_available": True,
        "afterhours_first_close": first_close,
        "afterhours_last_close": last_close,
        "afterhours_previous_regular_close": previous_close,
        "afterhours_session_return_pct": pct_change(last_close, first_close),
        "afterhours_last_vs_regular_close_pct": pct_change(last_close, previous_close),
        "afterhours_volume": total_volume,
        "afterhours_typical_prior_volume": typical_volume,
        "afterhours_relative_volume": total_volume / typical_volume if typical_volume else None,
        "afterhours_last_timestamp_et": afterhours[-1]["_stamp"].strftime("%Y-%m-%d %H:%M:%S"),
    })
    return base
