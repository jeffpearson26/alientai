from __future__ import annotations

"""Fail-closed paper adapter for the frozen contextual-options policy."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_ID = "contextual_options_shadow_v1"


def _avoid(reason: str) -> list[dict[str, Any]]:
    return [{
        "engine_id": POLICY_ID,
        "symbol": "",
        "side": "LONG",
        "score": 0.0,
        "decision": "AVOID",
        "price": 0.0,
        "reason": reason,
        "source": POLICY_ID,
    }]


def payload_path(settings: dict[str, Any], today: str) -> Path:
    configured = str(settings.get("contextual_options_daily_payload_path") or "").strip()
    payload_dir = PROJECT_ROOT / "data_v2" / "rcef_research"
    if configured:
        configured_path = Path(configured)
        return configured_path if configured_path.is_absolute() else PROJECT_ROOT / configured_path
    exact = payload_dir / f"contextual_options_shadow_payload_{today}.json"
    available = sorted(payload_dir.glob("contextual_options_shadow_payload_????-??-??.json"))
    return exact if exact.exists() else (available[-1] if available else exact)


def candidate_symbols(settings: dict[str, Any]) -> list[str]:
    timezone = ZoneInfo(str(settings.get("timezone") or "America/Los_Angeles"))
    today = datetime.now(timezone).date().isoformat()
    path = payload_path(settings, today)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return list(dict.fromkeys(
        str(row.get("symbol") or "").upper()
        for row in payload.get("candidates") or []
        if str(row.get("symbol") or "").strip()
    ))


def scan(quotes: list[dict[str, Any]], settings: dict[str, Any]) -> list[dict[str, Any]]:
    timezone = ZoneInfo(str(settings.get("timezone") or "America/Los_Angeles"))
    today = datetime.now(timezone).date().isoformat()
    current_payload_path = payload_path(settings, today)
    if not current_payload_path.exists():
        return _avoid(f"No complete same-day contextual-options payload for {today}.")
    try:
        payload = json.loads(current_payload_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return _avoid(f"Contextual-options payload could not be read: {exc}")
    try:
        payload_day = date.fromisoformat(str(payload.get("market_date") or ""))
        current_day = date.fromisoformat(today)
    except ValueError:
        return _avoid("Contextual-options payload has an invalid market date.")
    age = (current_day - payload_day).days
    maximum_age = max(0, int(settings.get("contextual_options_payload_max_calendar_age_days", 3)))
    if (
        payload.get("status") != "research_payload_ready"
        or payload.get("research_only") is not True
        or age < 0
        or age > maximum_age
        or int(payload.get("universe_rows") or 0) < 400
    ):
        return _avoid("Contextual-options payload failed freshness or completeness checks.")
    quote_map = {
        str(row.get("symbol") or "").upper(): row for row in quotes if isinstance(row, dict)
    }
    output = []
    for candidate in list(payload.get("candidates") or [])[:5]:
        if str(candidate.get("shadow_policy_id") or "") != POLICY_ID:
            continue
        if candidate.get("shadow_research_decision") != "BUY_CANDIDATE":
            continue
        symbol = str(candidate.get("symbol") or "").upper()
        quote = quote_map.get(symbol, {})
        try:
            price = float(quote.get("price") or quote.get("last_price") or quote.get("last") or 0.0)
            score = float(candidate.get("technical_context_score") or 0.0) * 100.0
            cutoff = float(candidate.get("shadow_policy_score_cutoff") or 0.0) * 100.0
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        output.append({
            **candidate,
            "engine_id": POLICY_ID,
            "decision": "BUY_CANDIDATE",
            "price": price,
            "score": max(0.0, min(100.0, score)),
            "model_score_pct": max(0.0, min(100.0, score)),
            "selection_cutoff_pct": max(0.0, min(100.0, cutoff)),
            "requested_position_dollars": price,
            "prediction_horizon_days": 5,
            "minimum_hold_minutes": 5 * 24 * 60,
            "reason": (
                "Paper-only contextual-options candidate from a complete validated "
                f"{payload_day.isoformat()} payload. {candidate.get('reason') or ''}"
            ).strip(),
            "source": POLICY_ID,
        })
    return output or _avoid("Current contextual-options payload contained no currently quotable candidates.")
