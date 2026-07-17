from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List

from alientai_v2.shadow_outcomes import OUTCOMES_PATH
from alientai_v2.utils import DATA_DIR, safe_float, save_json


SCORECARD_PATH = DATA_DIR / "shadow_engine_scorecard.json"


def summarize_engine_outcomes(
    outcomes: Iterable[Dict[str, Any]],
    min_completed_signals: int = 100,
    min_profit_factor: float = 1.20,
) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in outcomes:
        if isinstance(row, dict):
            grouped[str(row.get("engine_id") or "unknown_engine")].append(row)

    result: List[Dict[str, Any]] = []
    for engine_id, rows in grouped.items():
        returns = [safe_float(row.get("net_return_pct"), 0.0) for row in rows]
        wins = [value for value in returns if value > 0]
        losses = [value for value in returns if value < 0]
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
        avg_net = sum(returns) / len(returns) if returns else 0.0

        if len(rows) < min_completed_signals:
            classification = "INSUFFICIENT_DATA"
        elif avg_net > 0 and profit_factor is not None and profit_factor >= min_profit_factor:
            classification = "RESEARCH_PASS"
        else:
            classification = "FAILED"

        result.append({
            "engine_id": engine_id,
            "completed_signals": len(rows),
            "winning_signals": len(wins),
            "losing_signals": len(losses),
            "win_rate_pct": round(100.0 * len(wins) / len(rows), 4) if rows else 0.0,
            "avg_raw_return_pct": round(sum(safe_float(row.get("raw_return_pct"), 0.0) for row in rows) / len(rows), 6),
            "avg_net_return_pct": round(avg_net, 6),
            "profit_factor": round(profit_factor, 6) if profit_factor is not None else None,
            "classification": classification,
            "auto_trading_enabled": False,
        })
    result.sort(key=lambda row: (row["classification"] == "RESEARCH_PASS", row["avg_net_return_pct"]), reverse=True)
    return result


def build_shadow_engine_scorecard(settings: Dict[str, Any]) -> Dict[str, Any]:
    outcomes: List[Dict[str, Any]] = []
    if OUTCOMES_PATH.exists():
        for line in OUTCOMES_PATH.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                outcomes.append(json.loads(line))
    minimum = int(safe_float(settings.get("shadow_scorecard_min_completed_signals"), 100))
    min_pf = safe_float(settings.get("shadow_scorecard_min_profit_factor"), 1.20)
    engines = summarize_engine_outcomes(outcomes, minimum, min_pf)
    card = {
        "status": "success",
        "updated_at": datetime.now().replace(microsecond=0).isoformat(),
        "completed_outcomes": len(outcomes),
        "minimum_completed_signals": minimum,
        "minimum_profit_factor": min_pf,
        "engines": engines,
        "note": "Research classification only. This file never enables trading.",
    }
    save_json(SCORECARD_PATH, card)
    return card
