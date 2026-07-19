from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional


def number(value: Any) -> Optional[float]:
    try:
        return float(str(value).replace("%", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _empty() -> Dict[str, Any]:
    return {
        "institutional_holdings_available": False,
        "institutional_ownership_pct": None,
        "institutional_holder_count": None,
        "institutional_holder_net_increase_count": None,
        "institutional_share_net_change": None,
        "institutional_accumulation_ratio": None,
        "institutional_top10_concentration_pct": None,
        "institutional_days_since_latest_report": None,
    }


def institutional_holding_features(document: Mapping[str, Any], as_of_utc: str) -> Dict[str, Any]:
    output = _empty()
    collected = str(document.get("collected_at_utc") or "").strip()
    as_of = utc(as_of_utc)
    if not collected or utc(collected) > as_of:
        return output
    payload = document.get("payload") or {}
    total_shares = number(payload.get("total_institutional_shares"))
    increased = number(payload.get("shares_with_increased_holdings")) or 0.0
    decreased = number(payload.get("shares_with_decreased_holdings")) or 0.0
    holder_up = number(payload.get("holders_with_increased_holdings")) or 0.0
    holder_down = number(payload.get("holders_with_decreased_holdings")) or 0.0
    holdings = list(payload.get("holdings") or [])
    top10 = sorted((number(row.get("shares_held")) or 0.0 for row in holdings), reverse=True)[:10]
    report_days = []
    for row in holdings:
        try:
            day = datetime.fromisoformat(str(row.get("last_reported"))).date()
        except (TypeError, ValueError):
            continue
        if day <= as_of.date():
            report_days.append(day)
    denominator = increased + decreased
    output.update({
        "institutional_holdings_available": True,
        "institutional_ownership_pct": number(payload.get("total_institutional_ownership_percentage")),
        "institutional_holder_count": number(payload.get("total_institutional_holders")),
        "institutional_holder_net_increase_count": holder_up - holder_down,
        "institutional_share_net_change": increased - decreased,
        "institutional_accumulation_ratio": increased / denominator if denominator else None,
        "institutional_top10_concentration_pct": sum(top10) / total_shares * 100.0 if total_shares else None,
        "institutional_days_since_latest_report": (as_of.date() - max(report_days)).days if report_days else None,
    })
    return output
