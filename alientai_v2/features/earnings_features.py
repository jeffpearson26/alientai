from __future__ import annotations

"""Leakage-safe features from quarterly earnings events."""

from datetime import datetime, timezone
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number == number else None
    except (TypeError, ValueError):
        return None


def _timestamp(value: Any) -> datetime:
    raw = str(value or "").strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def visible_earnings(
    rows: Iterable[Mapping[str, Any]], symbol: str, as_of: Any,
) -> List[Mapping[str, Any]]:
    cutoff = _timestamp(as_of)
    ticker = str(symbol or "").upper().strip()
    visible = []
    for row in rows:
        if str(row.get("ticker") or "").upper().strip() != ticker:
            continue
        if not bool(row.get("is_training_eligible", True)):
            continue
        try:
            available = _timestamp(row.get("available_at_utc"))
        except (TypeError, ValueError):
            continue
        if available <= cutoff:
            visible.append(row)
    return sorted(visible, key=lambda row: _timestamp(row.get("available_at_utc")))


def build_earnings_features(
    rows: Iterable[Mapping[str, Any]], symbol: str, as_of: Any,
) -> Dict[str, Any]:
    cutoff = _timestamp(as_of)
    visible = visible_earnings(rows, symbol, cutoff)
    output: Dict[str, Any] = {
        "earnings_available": bool(visible),
        "earnings_visible_quarter_count": len(visible),
        "earnings_days_since_report": None,
        "earnings_reported_eps": None,
        "earnings_estimated_eps": None,
        "earnings_surprise": None,
        "earnings_surprise_percentage": None,
        "earnings_absolute_surprise_percentage": None,
        "earnings_beat": False,
        "earnings_miss": False,
        "earnings_average_surprise_percentage_4q": None,
        "earnings_beat_streak": 0,
        "earnings_post_report_1d": False,
        "earnings_post_report_5d": False,
        "earnings_post_report_10d": False,
    }
    if not visible:
        return output
    latest = visible[-1]
    available = _timestamp(latest.get("available_at_utc"))
    age_days = max(0.0, (cutoff - available).total_seconds() / 86400.0)
    surprise_pct = _number(latest.get("surprise_percentage"))
    surprise = _number(latest.get("surprise"))
    output.update({
        "earnings_days_since_report": round(age_days, 6),
        "earnings_reported_eps": _number(latest.get("reported_eps")),
        "earnings_estimated_eps": _number(latest.get("estimated_eps")),
        "earnings_surprise": surprise,
        "earnings_surprise_percentage": surprise_pct,
        "earnings_absolute_surprise_percentage": abs(surprise_pct) if surprise_pct is not None else None,
        "earnings_beat": bool(surprise is not None and surprise > 0),
        "earnings_miss": bool(surprise is not None and surprise < 0),
        "earnings_post_report_1d": age_days <= 1.0,
        "earnings_post_report_5d": age_days <= 5.0,
        "earnings_post_report_10d": age_days <= 10.0,
    })
    recent_surprises = [
        value for value in (_number(row.get("surprise_percentage")) for row in visible[-4:])
        if value is not None
    ]
    if recent_surprises:
        output["earnings_average_surprise_percentage_4q"] = round(mean(recent_surprises), 8)
    streak = 0
    for row in reversed(visible):
        value = _number(row.get("surprise"))
        if value is None or value <= 0:
            break
        streak += 1
    output["earnings_beat_streak"] = streak
    return output


def fetch_symbol_earnings(client: Any, symbol: str) -> List[Dict[str, Any]]:
    response = (
        client.table("v2_earnings_events").select("*")
        .eq("ticker", str(symbol).upper().strip())
        .eq("is_training_eligible", True)
        .order("available_at_utc").limit(500).execute()
    )
    return list(response.data or [])
