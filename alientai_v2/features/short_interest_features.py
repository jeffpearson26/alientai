from __future__ import annotations

"""Leakage-safe features from published short-interest snapshots."""

from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping

from alientai_v2.features.insider_purchase_features import safe_float, timestamp


def visible_short_interest(
    rows: Iterable[Mapping[str, Any]], symbol: str, as_of: Any,
) -> List[Mapping[str, Any]]:
    cutoff = timestamp(as_of)
    wanted = str(symbol or "").upper().strip()
    visible: List[Mapping[str, Any]] = []
    for row in rows:
        if str(row.get("ticker") or "").upper().strip() != wanted:
            continue
        if not bool(row.get("is_training_eligible", True)):
            continue
        try:
            available = timestamp(row.get("available_at_utc") or row.get("publication_timestamp_utc"))
        except ValueError:
            continue
        if available <= cutoff:
            visible.append(row)
    return sorted(
        visible,
        key=lambda row: (
            timestamp(row.get("available_at_utc") or row.get("publication_timestamp_utc")),
            str(row.get("settlement_date") or ""),
        ),
    )


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator > 0 else None


def build_short_interest_features(
    rows: Iterable[Mapping[str, Any]], symbol: str, as_of: Any,
) -> Dict[str, Any]:
    cutoff = timestamp(as_of)
    visible = visible_short_interest(rows, symbol, cutoff)
    empty: Dict[str, Any] = {
        "short_interest_available": False,
        "short_interest_shares": None,
        "short_interest_pct_float": None,
        "short_interest_pct_outstanding": None,
        "short_interest_days_to_cover": None,
        "short_interest_change_from_prior_pct": None,
        "short_interest_report_age_days": None,
        "short_interest_high_squeeze_pressure": False,
    }
    if not visible:
        return empty
    latest = visible[-1]
    shares = max(0.0, safe_float(latest.get("short_interest_shares")))
    float_shares = safe_float(latest.get("float_shares"))
    outstanding = safe_float(latest.get("shares_outstanding"))
    average_volume = safe_float(latest.get("average_daily_volume"))
    days_to_cover = safe_float(latest.get("days_to_cover"), -1.0)
    if days_to_cover < 0:
        calculated = _ratio(shares, average_volume)
        days_to_cover = calculated if calculated is not None else None
    pct_float_ratio = _ratio(shares, float_shares)
    pct_outstanding_ratio = _ratio(shares, outstanding)
    previous_shares = max(0.0, safe_float(visible[-2].get("short_interest_shares"))) if len(visible) >= 2 else 0.0
    change = ((shares / previous_shares) - 1.0) * 100.0 if previous_shares > 0 else None
    available = timestamp(latest.get("available_at_utc") or latest.get("publication_timestamp_utc"))
    pct_float = pct_float_ratio * 100.0 if pct_float_ratio is not None else None
    return {
        "short_interest_available": True,
        "short_interest_shares": round(shares, 4),
        "short_interest_pct_float": round(pct_float, 6) if pct_float is not None else None,
        "short_interest_pct_outstanding": round(pct_outstanding_ratio * 100.0, 6) if pct_outstanding_ratio is not None else None,
        "short_interest_days_to_cover": round(days_to_cover, 6) if days_to_cover is not None else None,
        "short_interest_change_from_prior_pct": round(change, 6) if change is not None else None,
        "short_interest_report_age_days": round((cutoff - available).total_seconds() / 86400.0, 6),
        "short_interest_high_squeeze_pressure": bool(
            pct_float is not None and pct_float >= 10.0
            and days_to_cover is not None and days_to_cover >= 3.0
        ),
    }
