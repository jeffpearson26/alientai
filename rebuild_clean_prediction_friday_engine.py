from pathlib import Path

path = Path("alientai_v2/engines/prediction_friday.py")

backup = Path("alientai_v2/engines/prediction_friday_BACKUP_BEFORE_CLEAN_REBUILD.py")
if path.exists():
    backup.write_text(path.read_text(encoding="utf-8-sig"), encoding="utf-8")

code = r'''
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


ENGINE_ID = "prediction_friday"
BUILD = "ALIENTAI_V2_PREDICTION_FRIDAY_ENGINE_CLEAN_V1"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = (
    PROJECT_ROOT
    / "data_v2"
    / "prediction_friday_daily_training"
    / "prediction_friday_symbol_policy.json"
)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def load_policy() -> Dict[str, Dict[str, Any]]:
    try:
        if POLICY_PATH.exists():
            data = json.loads(POLICY_PATH.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass

    return {}


def quote_symbol(row: Dict[str, Any]) -> str:
    return str(
        row.get("symbol")
        or row.get("ticker")
        or row.get("underlying_symbol")
        or ""
    ).upper().strip()


def quote_price(row: Dict[str, Any]) -> float:
    for key in [
        "last",
        "last_price",
        "price",
        "mark",
        "close",
    ]:
        value = safe_float(row.get(key), 0.0)
        if value > 0:
            return value
    return 0.0


def quote_close(row: Dict[str, Any]) -> float:
    for key in [
        "close",
        "previous_close",
        "prior_close",
        "regularMarketPreviousClose",
    ]:
        value = safe_float(row.get(key), 0.0)
        if value > 0:
            return value
    return 0.0


def quote_bid(row: Dict[str, Any]) -> float:
    return safe_float(row.get("bid") or row.get("bid_price"), 0.0)


def quote_ask(row: Dict[str, Any]) -> float:
    return safe_float(row.get("ask") or row.get("ask_price"), 0.0)


def quote_volume(row: Dict[str, Any]) -> float:
    return safe_float(row.get("volume") or row.get("totalVolume"), 0.0)


def spread_pct(row: Dict[str, Any], price: float) -> float:
    bid = quote_bid(row)
    ask = quote_ask(row)

    if bid > 0 and ask > 0 and ask >= bid:
        mid = (bid + ask) / 2.0
        if mid > 0:
            return ((ask - bid) / mid) * 100.0

    existing = safe_float(row.get("spread_pct") or row.get("spread_percent"), 0.0)
    return existing


def move_pct(row: Dict[str, Any], price: float) -> float:
    existing = row.get("move_pct")
    if existing is None:
        existing = row.get("net_change_percent")
    if existing is None:
        existing = row.get("change_percent")

    value = safe_float(existing, None)
    if value is not None:
        return value

    close = quote_close(row)
    if close > 0 and price > 0:
        return ((price - close) / close) * 100.0

    return 0.0


def decision_for_policy(policy: str, score: float, settings: Dict[str, Any]) -> str:
    policy = str(policy or "NO_DATA").upper().strip()

    buying_enabled = bool(settings.get("prediction_friday_buying_enabled", False))
    confirmation_only = bool(settings.get("prediction_friday_confirmation_only", True))

    allowed = settings.get("prediction_friday_buy_policies", ["ALLOW_BUY_STRONG"])
    if not isinstance(allowed, list):
        allowed = ["ALLOW_BUY_STRONG"]

    allowed = {str(x).upper().strip() for x in allowed}

    if policy in {"BLOCK_BUY", "NO_DATA", "UNKNOWN"}:
        return "AVOID"

    if policy == "WATCH_ONLY":
        return "WATCH"

    if policy in {"ALLOW_BUY_STRONG", "ALLOW_BUY"}:
        if confirmation_only or not buying_enabled:
            return "WATCH"

        if policy in allowed:
            return "BUY_CANDIDATE"

        return "WATCH"

    return "AVOID"


def score_for_policy(policy_row: Dict[str, Any], quote: Dict[str, Any]) -> float:
    win_rate = safe_float(policy_row.get("buy_candidate_win_rate_pct"), 0.0)
    avg_return = safe_float(policy_row.get("avg_buy_future_friday_return_pct"), 0.0)

    price = quote_price(quote)
    move = move_pct(quote, price)
    spread = spread_pct(quote, price)
    volume = quote_volume(quote)

    score = 0.0

    # Base historical edge.
    score += max(0.0, min(70.0, win_rate))

    # Reward useful average return.
    if avg_return > 0:
        score += min(15.0, avg_return * 5.0)

    # Current-day confirmation.
    if move > 0:
        score += 5.0
    if move > 1:
        score += 4.0
    if move > 3:
        score += 3.0

    # Basic liquidity and spread caution.
    if volume >= 100000:
        score += 4.0
    elif volume >= 25000:
        score += 2.0

    if spread > 5:
        score -= 8.0
    if spread > 10:
        score -= 10.0
    if spread > 20:
        score -= 15.0

    return round(max(0.0, min(100.0, score)), 4)


def scan(quotes: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    policy = load_policy()
    rows: List[Dict[str, Any]] = []

    if not policy:
        return [{
            "engine_id": ENGINE_ID,
            "symbol": "",
            "decision": "AVOID",
            "score": 0.0,
            "price": 0.0,
            "source": ENGINE_ID,
            "reason": f"Friday policy file not found or empty: {POLICY_PATH}",
        }]

    max_rows = int(safe_float(settings.get("prediction_friday_max_candidates", 80), 80))

    for quote in quotes:
        symbol = quote_symbol(quote)
        if not symbol:
            continue

        policy_row = policy.get(symbol)
        if not isinstance(policy_row, dict):
            rows.append({
                "engine_id": ENGINE_ID,
                "symbol": symbol,
                "side": "LONG",
                "score": 0.0,
                "decision": "AVOID",
                "price": quote_price(quote),
                "prediction_horizon_days": 5.0,
                "minimum_hold_minutes": safe_float(settings.get("prediction_friday_minimum_hold_minutes"), 7200.0),
                "source": ENGINE_ID,
                "prediction_friday_policy": "NO_DATA",
                "reason": "No Friday policy for this symbol.",
            })
            continue

        friday_policy = str(policy_row.get("policy") or "NO_DATA").upper().strip()
        score = score_for_policy(policy_row, quote)
        decision = decision_for_policy(friday_policy, score, settings)

        price = quote_price(quote)
        move = move_pct(quote, price)
        spread = spread_pct(quote, price)
        volume = quote_volume(quote)

        reason_parts = [
            f"FridayPolicy={friday_policy}",
            f"Friday buy win={policy_row.get('buy_candidate_win_rate_pct')}",
            f"Friday avg buy return={policy_row.get('avg_buy_future_friday_return_pct')}",
            f"records={policy_row.get('records')}",
            f"buy_candidates={policy_row.get('buy_candidates')}",
        ]

        if decision == "BUY_CANDIDATE":
            reason_parts.append("Friday buying enabled and policy allowed.")
        elif friday_policy in {"ALLOW_BUY_STRONG", "ALLOW_BUY"}:
            reason_parts.append("Friday policy is favorable but buying may be confirmation-only or policy not allowed.")

        warnings = []

        if spread > 5:
            warnings.append("Spread is wide for entry.")
        if volume < 25000:
            warnings.append("Thin volume for Friday prediction.")
        if move <= 0:
            warnings.append("Not positive today.")

        rows.append({
            "engine_id": ENGINE_ID,
            "symbol": symbol,
            "side": "LONG",
            "score": score,
            "decision": decision,
            "price": price,
            "prediction_horizon_minutes": 7200.0,
            "prediction_horizon_days": 5.0,
            "minimum_hold_minutes": safe_float(settings.get("prediction_friday_minimum_hold_minutes"), 7200.0),
            "source": ENGINE_ID,
            "reason": " ".join(reason_parts),
            "reasons": reason_parts,
            "warnings": warnings,
            "move_pct": round(move, 4),
            "spread_percent": round(spread, 4),
            "volume": volume,
            "prediction_friday_policy": friday_policy,
            "prediction_friday_policy_source": str(POLICY_PATH),
            "prediction_friday_buy_win_rate_pct": safe_float(policy_row.get("buy_candidate_win_rate_pct"), 0.0),
            "prediction_friday_avg_buy_return_pct": safe_float(policy_row.get("avg_buy_future_friday_return_pct"), 0.0),
            "prediction_friday_records": int(safe_float(policy_row.get("records"), 0)),
            "prediction_friday_buy_candidates": int(safe_float(policy_row.get("buy_candidates"), 0)),
            "raw_quote_summary": {
                "bid": quote_bid(quote),
                "ask": quote_ask(quote),
                "close": quote_close(quote),
            },
        })

    rows.sort(key=lambda r: safe_float(r.get("score"), 0.0), reverse=True)
    return rows[:max_rows]
'''

path.write_text(code, encoding="utf-8")
print("Rebuilt prediction_friday.py as clean Friday-policy engine.")
