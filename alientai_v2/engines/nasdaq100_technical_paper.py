from __future__ import annotations

"""Fail-closed adapter for the frozen Nasdaq-100 technical clone."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_ID = "nasdaq100_technical_clone_v1"


def _avoid(reason: str) -> list[dict[str, Any]]:
    return [{
        "engine_id": POLICY_ID, "symbol": "", "side": "LONG", "score": 0.0,
        "decision": "AVOID", "price": 0.0, "reason": reason, "source": POLICY_ID,
    }]


def payload_path(settings: dict[str, Any], today: str) -> Path:
    configured = str(settings.get("nasdaq100_daily_payload_path") or "").strip()
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else PROJECT_ROOT / path
    directory = PROJECT_ROOT / "data_v2" / "rcef_research" / "nasdaq100_clone"
    exact = directory / f"nasdaq100_paper_payload_{today}.json"
    available = sorted(directory.glob("nasdaq100_paper_payload_????-??-??.json"))
    return exact if exact.exists() else (available[-1] if available else exact)


def candidate_symbols(settings: dict[str, Any]) -> list[str]:
    timezone = ZoneInfo(str(settings.get("timezone") or "America/Los_Angeles"))
    path = payload_path(settings, datetime.now(timezone).date().isoformat())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [
        str(row.get("symbol") or "").upper()
        for row in payload.get("candidates") or []
        if str(row.get("symbol") or "").strip()
    ]


def scan(quotes: list[dict[str, Any]], settings: dict[str, Any]) -> list[dict[str, Any]]:
    timezone = ZoneInfo(str(settings.get("timezone") or "America/Los_Angeles"))
    today = datetime.now(timezone).date()
    path = payload_path(settings, today.isoformat())
    if not path.exists():
        return _avoid(f"No Nasdaq-100 paper payload is available for {today.isoformat()}.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload_day = date.fromisoformat(str(payload.get("market_date") or ""))
    except Exception as exc:
        return _avoid(f"Nasdaq-100 payload could not be read: {exc}")
    maximum_age = max(0, int(settings.get("nasdaq100_payload_max_calendar_age_days", 3)))
    if (
        payload.get("status") != "paper_payload_ready"
        or payload.get("research_only") is not True
        or payload.get("paper_only") is not True
        or payload.get("live_trading_enabled") is not False
        or payload.get("policy_id") != POLICY_ID
        or (today - payload_day).days not in range(maximum_age + 1)
        or int(payload.get("training_universe_size") or 0) != 80
        or len(set(payload.get("training_universe_symbols") or [])) != 80
        or int(payload.get("universe_rows") or 0) < 75
    ):
        return _avoid("Nasdaq-100 payload failed identity, freshness, or completeness checks.")
    quotes_by_symbol = {
        str(row.get("symbol") or "").upper(): row for row in quotes if isinstance(row, dict)
    }
    output = []
    for candidate in (payload.get("candidates") or [])[:5]:
        if candidate.get("policy_id") != POLICY_ID or candidate.get("paper_decision") != "BUY_CANDIDATE":
            continue
        symbol = str(candidate.get("symbol") or "").upper()
        if symbol not in set(payload["training_universe_symbols"]):
            continue
        quote = quotes_by_symbol.get(symbol, {})
        try:
            price = float(quote.get("price") or quote.get("last_price") or quote.get("last") or 0.0)
            raw_score = float(candidate["technical_context_score"])
            cutoff = float(candidate["locked_score_cutoff"])
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0 or raw_score < cutoff:
            continue
        output.append({
            **candidate,
            "engine_id": POLICY_ID,
            "side": "LONG",
            "decision": "BUY_CANDIDATE",
            "price": price,
            "score": max(0.0, min(100.0, raw_score * 100.0)),
            "model_score_pct": max(0.0, min(100.0, raw_score * 100.0)),
            "selection_cutoff_pct": cutoff * 100.0,
            "requested_position_dollars": price,
            "prediction_horizon_days": 5,
            "minimum_hold_minutes": 5 * 24 * 60,
            "reason": "Paper-only frozen Nasdaq-100 technical clone candidate.",
            "source": POLICY_ID,
        })
    return output or _avoid("Current Nasdaq-100 payload contained no quotable candidates above the frozen cutoff.")
