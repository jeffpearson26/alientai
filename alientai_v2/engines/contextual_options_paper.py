from __future__ import annotations

"""Fail-closed paper adapter for the frozen contextual-options policy."""

import json
from datetime import datetime
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


def scan(quotes: list[dict[str, Any]], settings: dict[str, Any]) -> list[dict[str, Any]]:
    timezone = ZoneInfo(str(settings.get("timezone") or "America/Los_Angeles"))
    today = datetime.now(timezone).date().isoformat()
    configured = str(settings.get("contextual_options_daily_payload_path") or "").strip()
    payload_path = (
        PROJECT_ROOT / configured
        if configured
        else PROJECT_ROOT / "data_v2" / "rcef_research" / f"contextual_options_shadow_payload_{today}.json"
    )
    if not payload_path.exists():
        return _avoid(f"No complete same-day contextual-options payload for {today}.")
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return _avoid(f"Contextual-options payload could not be read: {exc}")
    if (
        payload.get("status") != "research_payload_ready"
        or payload.get("research_only") is not True
        or str(payload.get("market_date") or "") != today
        or int(payload.get("universe_rows") or 0) < 400
    ):
        return _avoid("Contextual-options payload failed same-day completeness checks.")
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
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        output.append({
            **candidate,
            "engine_id": POLICY_ID,
            "decision": "BUY_CANDIDATE",
            "price": price,
            "score": max(55.0, min(100.0, score)),
            "prediction_horizon_days": 5,
            "minimum_hold_minutes": 5 * 24 * 60,
            "reason": (
                "Paper-only contextual-options candidate from a complete validated "
                f"{today} payload. {candidate.get('reason') or ''}"
            ).strip(),
            "source": POLICY_ID,
        })
    return output or _avoid("Same-day contextual-options payload contained no currently quotable candidates.")
