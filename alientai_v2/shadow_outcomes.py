from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Set
from zoneinfo import ZoneInfo

from alientai_v2.shadow_signals import JOURNAL_PATH, candidate_price
from alientai_v2.utils import DATA_DIR, load_json, now_iso, safe_float, save_json


OUTCOMES_PATH = DATA_DIR / "shadow_signal_outcomes.jsonl"
OUTCOME_INDEX_PATH = DATA_DIR / "shadow_signal_outcomes_index.json"


def parse_time(value: str, timezone_name: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(timezone_name))
        return dt
    except Exception:
        return None


def due_time(signal: Dict[str, Any], timezone_name: str) -> datetime | None:
    scheduled = parse_time(str(signal.get("scheduled_exit_time") or ""), timezone_name)
    if scheduled:
        return scheduled
    observed = parse_time(str(signal.get("observed_at") or ""), timezone_name)
    if not observed:
        return None
    minutes = safe_float(signal.get("prediction_horizon_minutes"), 0.0)
    days = safe_float(signal.get("prediction_horizon_days"), 0.0)
    if minutes > 0:
        return observed + timedelta(minutes=minutes)
    if days > 0:
        return observed + timedelta(days=days)
    return None


def quote_map(quotes: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for quote in quotes:
        symbol = str(quote.get("symbol") or "").upper().strip()
        price = candidate_price(quote)
        if symbol and price > 0:
            result[symbol] = price
    return result


def build_due_outcomes(
    signals: Iterable[Dict[str, Any]],
    quotes: Iterable[Dict[str, Any]],
    settings: Dict[str, Any],
    evaluated_at: str,
    completed_keys: Set[str],
) -> List[Dict[str, Any]]:
    timezone_name = str(settings.get("timezone") or "America/Los_Angeles")
    now = parse_time(evaluated_at, timezone_name)
    if not now:
        return []
    prices = quote_map(quotes)
    cost_pct = max(0.0, safe_float(settings.get("shadow_signal_round_trip_cost_pct"), 0.25))
    outcomes: List[Dict[str, Any]] = []
    for signal in signals:
        key = str(signal.get("signal_key") or "")
        if not key or key in completed_keys:
            continue
        target = due_time(signal, timezone_name)
        if not target or now.timestamp() < target.timestamp():
            continue
        symbol = str(signal.get("symbol") or "").upper().strip()
        exit_price = prices.get(symbol, 0.0)
        entry_price = safe_float(signal.get("observed_price"), 0.0)
        if entry_price <= 0 or exit_price <= 0:
            continue
        raw_return = ((exit_price - entry_price) / entry_price) * 100.0
        completed_keys.add(key)
        outcomes.append({
            "signal_key": key,
            "evaluated_at": evaluated_at,
            "due_at": target.isoformat(),
            "symbol": symbol,
            "engine_id": str(signal.get("engine_id") or "unknown_engine"),
            "entry_price": round(entry_price, 6),
            "exit_price": round(exit_price, 6),
            "raw_return_pct": round(raw_return, 6),
            "cost_assumption_pct": cost_pct,
            "net_return_pct": round(raw_return - cost_pct, 6),
            "win_after_cost": raw_return - cost_pct > 0,
            "status": "COMPLETED_RESEARCH_SIGNAL",
        })
    return outcomes


def evaluate_due_shadow_signals(quotes: Iterable[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:
    if not JOURNAL_PATH.exists():
        return {"status": "no_signals", "recorded": 0}
    signals = []
    for line in JOURNAL_PATH.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            signals.append(json.loads(line))
    index = load_json(OUTCOME_INDEX_PATH, {"keys": []})
    completed = {str(value) for value in index.get("keys", [])} if isinstance(index, dict) else set()
    evaluated_at = now_iso()
    outcomes = build_due_outcomes(signals, quotes, settings, evaluated_at, completed)
    if outcomes:
        with OUTCOMES_PATH.open("a", encoding="utf-8", newline="\n") as handle:
            for outcome in outcomes:
                handle.write(json.dumps(outcome, separators=(",", ":")) + "\n")
        save_json(OUTCOME_INDEX_PATH, {"updated_at": evaluated_at, "keys": sorted(completed)})
    return {"status": "success", "recorded": len(outcomes), "outcomes": str(OUTCOMES_PATH)}
