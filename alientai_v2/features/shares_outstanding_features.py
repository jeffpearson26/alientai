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


def change_pct(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous in (None, 0):
        return None
    return (current / previous - 1.0) * 100.0


def _empty() -> Dict[str, Any]:
    return {
        "shares_outstanding_available": False,
        "shares_outstanding_basic": None,
        "shares_outstanding_diluted": None,
        "shares_dilution_pct": None,
        "shares_basic_qoq_change_pct": None,
        "shares_basic_yoy_change_pct": None,
        "shares_days_since_report": None,
    }


def shares_outstanding_features(document: Mapping[str, Any], as_of_utc: str) -> Dict[str, Any]:
    output = _empty()
    collected = str(document.get("collected_at_utc") or "").strip()
    as_of = utc(as_of_utc)
    if not collected or utc(collected) > as_of:
        return output
    rows = []
    for row in (document.get("payload") or {}).get("data") or []:
        try:
            day = datetime.fromisoformat(str(row["date"])).date()
        except (KeyError, ValueError):
            continue
        if day <= as_of.date():
            rows.append((day, row))
    if not rows:
        return output
    rows.sort(key=lambda item: item[0], reverse=True)
    day, latest = rows[0]
    basic = number(latest.get("shares_outstanding_basic"))
    diluted = number(latest.get("shares_outstanding_diluted"))
    prior_quarter = number(rows[1][1].get("shares_outstanding_basic")) if len(rows) > 1 else None
    prior_year = number(rows[4][1].get("shares_outstanding_basic")) if len(rows) > 4 else None
    output.update({
        "shares_outstanding_available": True,
        "shares_outstanding_basic": basic,
        "shares_outstanding_diluted": diluted,
        "shares_dilution_pct": ((diluted / basic - 1.0) * 100.0) if basic not in (None, 0) and diluted is not None else None,
        "shares_basic_qoq_change_pct": change_pct(basic, prior_quarter),
        "shares_basic_yoy_change_pct": change_pct(basic, prior_year),
        "shares_days_since_report": (as_of.date() - day).days,
    })
    return output
