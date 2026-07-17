from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from alientai_v2.utils import DATA_DIR, load_json, now_iso, safe_float, save_json


JOURNAL_PATH = DATA_DIR / "shadow_signals.jsonl"
INDEX_PATH = DATA_DIR / "shadow_signals_index.json"


def candidate_price(row: Dict[str, Any]) -> float:
    for key in ("price", "last", "last_price", "mark", "close"):
        value = safe_float(row.get(key), 0.0)
        if value > 0:
            return value
    return 0.0


def signal_key(row: Dict[str, Any], observed_at: str, decision: str = "") -> str:
    day = str(observed_at)[:10]
    engine = str(row.get("engine_id") or "unknown_engine").strip()
    symbol = str(row.get("symbol") or "").upper().strip()
    decision = str(decision or row.get("decision") or "").upper().strip()
    return "|".join((day, engine, symbol, decision))


def build_new_records(
    scored: Iterable[Dict[str, Any]],
    settings: Dict[str, Any],
    observed_at: str,
    seen_keys: Set[str],
) -> List[Dict[str, Any]]:
    decisions = settings.get(
        "shadow_signal_decisions",
        ["BUY_CANDIDATE", "STRONG_BUY_CANDIDATE"],
    )
    if not isinstance(decisions, list):
        decisions = ["BUY_CANDIDATE", "STRONG_BUY_CANDIDATE"]
    wanted = {str(value).upper().strip() for value in decisions}
    records: List[Dict[str, Any]] = []

    for row in scored:
        if not isinstance(row, dict):
            continue
        execution_decision = str(row.get("decision") or "").upper().strip()
        shadow_decision = str(row.get("shadow_research_decision") or "").upper().strip()
        decision = shadow_decision or execution_decision
        symbol = str(row.get("symbol") or "").upper().strip()
        if decision not in wanted or not symbol:
            continue
        key = signal_key(row, observed_at, decision)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        engine_id = str(row.get("engine_id") or "unknown_engine").strip()
        allowlist = settings.get("main_account_enabled_buy_engines", [])
        if not isinstance(allowlist, list):
            allowlist = []
        allowlisted = engine_id in {str(value).strip() for value in allowlist}
        records.append({
            "signal_key": key,
            "observed_at": observed_at,
            "symbol": symbol,
            "engine_id": engine_id,
            "decision": decision,
            "execution_decision": execution_decision,
            "shadow_research_only": bool(shadow_decision),
            "score": safe_float(row.get("score"), 0.0),
            "observed_price": candidate_price(row),
            "prediction_horizon_minutes": safe_float(row.get("prediction_horizon_minutes"), 0.0),
            "prediction_horizon_days": safe_float(row.get("prediction_horizon_days"), 0.0),
            "scheduled_exit_time": str(row.get("scheduled_exit_time") or ""),
            "exit_rule": str(row.get("exit_rule") or ""),
            "spread_percent": safe_float(row.get("spread_percent") or row.get("spread_pct"), 0.0),
            "main_account_allowlisted": allowlisted,
            "paper_trading_enabled_at_signal": bool(settings.get("paper_trading_enabled", False)),
            "reason": str(row.get("reason") or ""),
            "status": "OPEN_RESEARCH_SIGNAL",
        })
    return records


def record_shadow_signals(scored: Iterable[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:
    if not bool(settings.get("shadow_signal_journal_enabled", True)):
        return {"status": "disabled", "recorded": 0}

    index = load_json(INDEX_PATH, {"keys": []})
    keys = index.get("keys", []) if isinstance(index, dict) else []
    seen = {str(value) for value in keys}
    observed_at = now_iso()
    records = build_new_records(scored, settings, observed_at, seen)

    if records:
        JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with JOURNAL_PATH.open("a", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, separators=(",", ":")) + "\n")
        save_json(INDEX_PATH, {"updated_at": observed_at, "keys": sorted(seen)})

    return {"status": "success", "recorded": len(records), "journal": str(JOURNAL_PATH)}
