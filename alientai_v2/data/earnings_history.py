from __future__ import annotations

"""Normalize Alpha Vantage quarterly earnings into point-in-time events."""

import hashlib
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping
from zoneinfo import ZoneInfo


EASTERN = ZoneInfo("America/New_York")


def _text(value: Any) -> str:
    raw = str(value or "").strip()
    return "" if raw.lower() in {"none", "null", "nan"} else raw


def _number(value: Any) -> float | None:
    raw = _text(value)
    if not raw:
        return None
    try:
        number = float(raw.replace("%", "").replace(",", ""))
        return number if number == number else None
    except ValueError:
        return None


def conservative_available_at(reported_date: str, report_time: str) -> str:
    day = date.fromisoformat(reported_date)
    timing = _text(report_time).lower().replace("_", "").replace("-", "")
    if timing in {"premarket", "beforemarketopen", "bmo"}:
        local = datetime.combine(day, time(9, 25), tzinfo=EASTERN)
    elif timing in {"postmarket", "aftermarketclose", "amc"}:
        local = datetime.combine(day, time(16, 30), tzinfo=EASTERN)
    else:
        # Unknown timing is made visible the next day to prevent same-day leakage.
        local = datetime.combine(day + timedelta(days=1), time(9, 25), tzinfo=EASTERN)
    return local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_quarter(symbol: str, row: Mapping[str, Any]) -> Dict[str, Any]:
    ticker = _text(symbol).upper()
    fiscal_date = _text(row.get("fiscalDateEnding"))
    reported_date = _text(row.get("reportedDate"))
    if not ticker or not fiscal_date or not reported_date:
        raise ValueError("earnings event requires ticker, fiscal date, and reported date")
    report_time = _text(row.get("reportTime"))
    identity = f"ALPHA_VANTAGE|{ticker}|{fiscal_date}|{reported_date}"
    event_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    reported_eps = _number(row.get("reportedEPS"))
    estimated_eps = _number(row.get("estimatedEPS"))
    surprise = _number(row.get("surprise"))
    surprise_pct = _number(row.get("surprisePercentage"))
    quality_flags: List[str] = []
    if reported_eps is None:
        quality_flags.append("MISSING_REPORTED_EPS")
    if estimated_eps is None:
        quality_flags.append("MISSING_ESTIMATED_EPS")
    return {
        "event_id": event_id,
        "ticker": ticker,
        "fiscal_date_ending": fiscal_date,
        "reported_date": reported_date,
        "report_time": report_time,
        "available_at_utc": conservative_available_at(reported_date, report_time),
        "reported_eps": reported_eps,
        "estimated_eps": estimated_eps,
        "surprise": surprise,
        "surprise_percentage": surprise_pct,
        "source": "ALPHA_VANTAGE_EARNINGS",
        "source_url": "https://www.alphavantage.co/query?function=EARNINGS",
        "quality_flags": quality_flags,
        "is_training_eligible": reported_eps is not None,
    }


def normalize_response(symbol: str, payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    if payload.get("Note") or payload.get("Information"):
        raise RuntimeError(str(payload.get("Note") or payload.get("Information")))
    rows = payload.get("quarterlyEarnings")
    if not isinstance(rows, list):
        raise ValueError("Alpha Vantage response lacks quarterlyEarnings")
    output = [normalize_quarter(symbol, row) for row in rows]
    return sorted(output, key=lambda row: (row["available_at_utc"], row["event_id"]))


def merge_events(existing: Iterable[Mapping[str, Any]], new_rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for row in list(existing) + list(new_rows):
        if row.get("event_id"):
            merged[str(row["event_id"])] = dict(row)
    return sorted(merged.values(), key=lambda row: (row.get("available_at_utc", ""), row["event_id"]))
