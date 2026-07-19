from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional


def number(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def pct_change(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous in (None, 0):
        return None
    return (current / previous - 1.0) * 100.0


def _empty() -> Dict[str, Any]:
    return {
        "earnings_estimate_available": False,
        "earnings_estimate_days_to_period_end": None,
        "earnings_estimate_eps_average": None,
        "earnings_estimate_eps_change_7d_pct": None,
        "earnings_estimate_eps_change_30d_pct": None,
        "earnings_estimate_eps_change_60d_pct": None,
        "earnings_estimate_eps_change_90d_pct": None,
        "earnings_estimate_revision_net_7d": None,
        "earnings_estimate_revision_net_30d": None,
        "earnings_estimate_analyst_count": None,
        "earnings_estimate_dispersion_pct": None,
        "revenue_estimate_analyst_count": None,
    }


def earnings_estimate_features(document: Mapping[str, Any], as_of_utc: str) -> Dict[str, Any]:
    output = _empty()
    collected = str(document.get("collected_at_utc") or "").strip()
    if not collected or utc(collected) > utc(as_of_utc):
        return output
    payload = document.get("payload") or {}
    candidates = []
    as_of_date = utc(as_of_utc).date()
    for estimate in payload.get("estimates") or []:
        if str(estimate.get("horizon") or "").lower() != "fiscal quarter":
            continue
        try:
            period_end = datetime.fromisoformat(str(estimate["date"])).date()
        except (KeyError, ValueError):
            continue
        if period_end >= as_of_date:
            candidates.append((period_end, estimate))
    if not candidates:
        return output
    period_end, estimate = min(candidates, key=lambda item: item[0])
    current = number(estimate.get("eps_estimate_average"))
    high, low = number(estimate.get("eps_estimate_high")), number(estimate.get("eps_estimate_low"))
    up7 = number(estimate.get("eps_estimate_revision_up_trailing_7_days")) or 0.0
    down7 = number(estimate.get("eps_estimate_revision_down_trailing_7_days")) or 0.0
    up30 = number(estimate.get("eps_estimate_revision_up_trailing_30_days")) or 0.0
    down30 = number(estimate.get("eps_estimate_revision_down_trailing_30_days")) or 0.0
    output.update({
        "earnings_estimate_available": True,
        "earnings_estimate_days_to_period_end": (period_end - as_of_date).days,
        "earnings_estimate_eps_average": current,
        "earnings_estimate_eps_change_7d_pct": pct_change(current, number(estimate.get("eps_estimate_average_7_days_ago"))),
        "earnings_estimate_eps_change_30d_pct": pct_change(current, number(estimate.get("eps_estimate_average_30_days_ago"))),
        "earnings_estimate_eps_change_60d_pct": pct_change(current, number(estimate.get("eps_estimate_average_60_days_ago"))),
        "earnings_estimate_eps_change_90d_pct": pct_change(current, number(estimate.get("eps_estimate_average_90_days_ago"))),
        "earnings_estimate_revision_net_7d": up7 - down7,
        "earnings_estimate_revision_net_30d": up30 - down30,
        "earnings_estimate_analyst_count": number(estimate.get("eps_estimate_analyst_count")),
        "earnings_estimate_dispersion_pct": ((high - low) / abs(current) * 100.0) if None not in (high, low, current) and current != 0 else None,
        "revenue_estimate_analyst_count": number(estimate.get("revenue_estimate_analyst_count")),
    })
    return output
