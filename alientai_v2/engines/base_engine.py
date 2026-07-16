from __future__ import annotations

from typing import Any, Dict, List


def make_candidate(
    *,
    engine_id: str,
    symbol: str,
    side: str,
    score: float,
    decision: str,
    price: float,
    prediction_horizon_minutes: float,
    minimum_hold_minutes: float,
    reason: str,
    quote: Dict[str, Any],
    warnings: List[str] | None = None,
    reasons: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Standard candidate format used by all AlientAI V2 engines.

    Every engine must return candidates in this shape so the paper account
    can buy, track, and later judge each engine fairly.
    """

    prediction_horizon_days = prediction_horizon_minutes / 1440.0 if prediction_horizon_minutes else 0.0

    return {
        "engine_id": engine_id,
        "symbol": str(symbol).upper(),
        "side": side.upper(),
        "score": round(float(score), 2),
        "decision": decision,
        "price": round(float(price), 4),
        "prediction_horizon_minutes": float(prediction_horizon_minutes),
        "prediction_horizon_days": round(float(prediction_horizon_days), 4),
        "minimum_hold_minutes": float(minimum_hold_minutes),
        "reason": reason,
        "reasons": reasons or [],
        "warnings": warnings or [],

        "move_pct": quote.get("net_change_percent"),
        "relative_volume": quote.get("relative_volume"),
        "spread_percent": quote.get("spread_percent"),
        "volume": quote.get("volume"),
        "source": quote.get("source"),
        "raw_quote_summary": {
            "bid": quote.get("bid"),
            "ask": quote.get("ask"),
            "close": quote.get("close"),
        },
    }
