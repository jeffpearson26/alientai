from __future__ import annotations

import csv

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from alientai_v2.features.pattern_features import (
    build_pattern_features,
    feature_distance,
    forward_outcome,
    safe_float,
    summarize_similar_outcomes,
)
from alientai_v2.history.supabase_candle_reader import fetch_symbol_candles



PROJECT_ROOT = Path(__file__).resolve().parents[2]
SIMILARITY_POLICY_PATH = PROJECT_ROOT / "data_v2" / "similarity_replay_training" / "similarity_symbol_policy.json"



LOCAL_5M_HISTORY_DIR = PROJECT_ROOT / "data_v2" / "russell_2000_5m_schwab_max"


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def read_local_symbol_candles(symbol: str, limit: int = 5000) -> List[Dict[str, Any]]:
    """
    Fallback history reader.

    The live similarity engine normally reads from Supabase.
    If Supabase has no rows for a symbol, this reads the local max-history CSV
    that we downloaded from Schwab.

    File pattern:
        data_v2/russell_2000_5m_schwab_max/SYMBOL_schwab_5m_max.csv
    """
    symbol = str(symbol or "").upper().strip()

    if not symbol:
        return []

    path = LOCAL_5M_HISTORY_DIR / f"{symbol}_schwab_5m_max.csv"

    if not path.exists():
        return []

    rows: List[Dict[str, Any]] = []

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for raw in reader:
                row_symbol = str(raw.get("symbol") or symbol).upper().strip()
                datetime_ms = safe_int(raw.get("datetime_ms"), 0)

                if not row_symbol or datetime_ms <= 0:
                    continue

                rows.append({
                    "symbol": row_symbol,
                    "datetime_ms": datetime_ms,
                    "datetime_utc": str(raw.get("datetime_utc") or ""),
                    "open": safe_float(raw.get("open"), 0.0),
                    "high": safe_float(raw.get("high"), 0.0),
                    "low": safe_float(raw.get("low"), 0.0),
                    "close": safe_float(raw.get("close"), 0.0),
                    "volume": safe_float(raw.get("volume"), 0.0),
                    "history_source": "local_csv",
                })
    except Exception:
        return []

    rows.sort(key=lambda r: int(r.get("datetime_ms") or 0))

    if limit and limit > 0 and len(rows) > limit:
        rows = rows[-limit:]

    return rows


def fetch_history_with_fallback(symbol: str, limit: int = 5000) -> tuple[List[Dict[str, Any]], str]:
    """
    Returns:
        candles, history_source

    Source can be:
        supabase
        local_csv
        none
    """
    candles: List[Dict[str, Any]] = []

    try:
        candles = fetch_symbol_candles(symbol, limit=limit)
    except Exception:
        candles = []

    if candles:
        for row in candles:
            if isinstance(row, dict):
                row.setdefault("history_source", "supabase")
        return candles, "supabase"

    candles = read_local_symbol_candles(symbol, limit=limit)

    if candles:
        return candles, "local_csv"

    return [], "none"


def load_similarity_symbol_policy() -> Dict[str, Any]:
    """
    Loads replay-built symbol policy.

    If the file is missing, the engine still works, but it will not allow
    similarity buys unless settings explicitly allow unproven symbols.
    """
    if not SIMILARITY_POLICY_PATH.exists():
        return {
            "allow_symbols": [],
            "watch_only_symbols": [],
            "block_symbols": [],
            "missing": True,
        }

    try:
        import json
        return json.loads(SIMILARITY_POLICY_PATH.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {
            "allow_symbols": [],
            "watch_only_symbols": [],
            "block_symbols": [],
            "error": str(exc),
        }


def policy_for_symbol(symbol: str, policy: Dict[str, Any]) -> str:
    symbol = str(symbol or "").upper().strip()

    allow = set(str(x).upper().strip() for x in policy.get("allow_symbols", []))
    watch = set(str(x).upper().strip() for x in policy.get("watch_only_symbols", []))
    block = set(str(x).upper().strip() for x in policy.get("block_symbols", []))

    if symbol in allow:
        return "ALLOW_BUY"

    if symbol in watch:
        return "WATCH_ONLY"

    if symbol in block:
        return "BLOCK_BUY"

    return "UNPROVEN"

ENGINE_ID = "similarity_engine"


def quote_symbol(quote: Dict[str, Any]) -> str:
    return str(quote.get("symbol") or "").upper().strip()


def quote_price(quote: Dict[str, Any]) -> float:
    for key in ("price", "last", "last_price", "mark", "close"):
        value = safe_float(quote.get(key), 0.0)
        if value > 0:
            return value
    return 0.0


def quote_move_pct(quote: Dict[str, Any]) -> float:
    for key in ("move_pct", "net_change_percent", "percentChange", "regularMarketPercentChange"):
        return safe_float(quote.get(key), 0.0)
    return 0.0


def quote_spread_pct(quote: Dict[str, Any]) -> float:
    for key in ("spread_pct", "spread_percent"):
        return safe_float(quote.get(key), 0.0)
    return 0.0


def quote_volume(quote: Dict[str, Any]) -> float:
    for key in ("volume", "totalVolume"):
        return safe_float(quote.get(key), 0.0)
    return 0.0


def historical_similarity_score(summary: Dict[str, float], settings: Dict[str, Any]) -> float:
    cases = safe_float(summary.get("cases"), 0.0)
    win_rate = safe_float(summary.get("win_rate_pct"), 0.0)
    avg_return = safe_float(summary.get("avg_forward_return_pct"), 0.0)
    avg_gain = safe_float(summary.get("avg_max_gain_pct"), 0.0)
    avg_drawdown = safe_float(summary.get("avg_max_drawdown_pct"), 0.0)

    min_cases = safe_float(settings.get("similarity_min_cases", 20), 20)

    if cases < min_cases:
        return 0.0

    score = 0.0

    # Base from win rate.
    # 50% = neutral. 60% = strong.
    score += (win_rate - 45.0) * 2.0

    # Reward positive average future movement.
    score += avg_return * 12.0

    # Reward upside potential.
    score += avg_gain * 3.0

    # Penalize drawdown. avg_drawdown is normally negative.
    score += avg_drawdown * 2.5

    # More cases gives confidence, capped.
    score += min(10.0, cases / 10.0)

    # Keep score in dashboard-friendly range.
    if score < 0:
        score = 0.0

    if score > 100:
        score = 100.0

    return round(score, 2)


def decision_from_score(score: float, settings: Dict[str, Any]) -> str:
    buy_score = safe_float(settings.get("similarity_buy_score", 62), 62)
    watch_score = safe_float(settings.get("similarity_watch_score", 45), 45)

    if score >= buy_score:
        return "BUY_CANDIDATE"

    if score >= watch_score:
        return "WATCH"

    return "AVOID"


def build_current_pseudo_candle_history(quote: Dict[str, Any], historical: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    V1 does not yet have live recent 5-minute candle streaming.
    So we use historical candles plus one pseudo-current candle from the live quote.

    This is not perfect, but it lets the similarity engine work immediately.
    Later we should feed it live intraday candle cache.
    """

    price = quote_price(quote)

    if price <= 0:
        return historical

    volume = quote_volume(quote)

    pseudo = {
        "symbol": quote_symbol(quote),
        "datetime_ms": 9999999999999,
        "open": price,
        "high": price,
        "low": price,
        "close": price,
        "volume": volume,
    }

    return historical + [pseudo]


def find_similar_cases(
    candles: List[Dict[str, Any]],
    current_features: Dict[str, float],
    *,
    window: int,
    horizon_bars: int,
    max_cases_to_scan: int,
    top_k: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, float]]]:
    """
    Scans historical candle windows and finds top similar patterns.

    We avoid the latest section so the current pseudo-candle does not contaminate outcomes.
    """

    if len(candles) < window + horizon_bars + 10:
        return [], []

    latest_safe_index = len(candles) - horizon_bars - 2

    start_min = window
    start_max = max(start_min, latest_safe_index)

    # Limit scan size for live speed. Use the most recent history first.
    possible_indices = list(range(start_min, start_max))

    if max_cases_to_scan > 0 and len(possible_indices) > max_cases_to_scan:
        possible_indices = possible_indices[-max_cases_to_scan:]

    scored_cases: List[Tuple[float, int, Dict[str, float]]] = []

    for idx in possible_indices:
        past_slice = candles[:idx + 1]
        features = build_pattern_features(past_slice, window=window)

        if not features:
            continue

        distance = feature_distance(current_features, features)
        scored_cases.append((distance, idx, features))

    scored_cases.sort(key=lambda x: x[0])

    top = scored_cases[:top_k]

    similar_cases = []
    outcomes = []

    for distance, idx, features in top:
        outcome = forward_outcome(candles, idx, horizon_bars=horizon_bars)

        if not outcome:
            continue

        case = {
            "distance": round(distance, 6),
            "index": idx,
            "features": features,
            "outcome": outcome,
        }

        similar_cases.append(case)
        outcomes.append(outcome)

    return similar_cases, outcomes


def run(quotes: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Clean V2 engine entrypoint.

    Input:
      quotes: live quote rows from V2 quote client
      settings: data_v2/v2_settings.json

    Output:
      candidate rows that engine_registry can combine with other engines.
    """

    enabled = bool(settings.get("similarity_engine_enabled", True))

    if not enabled:
        return []

    window = int(settings.get("similarity_window_bars", 12))
    horizon_bars = int(settings.get("similarity_horizon_bars", 78))
    history_limit = int(settings.get("similarity_history_limit", 5000))
    max_cases_to_scan = int(settings.get("similarity_max_cases_to_scan", 2500))
    top_k = int(settings.get("similarity_top_k", 50))
    min_cases = int(settings.get("similarity_min_cases", 20))
    max_symbols = int(settings.get("similarity_max_symbols_per_scan", 25))

    policy = load_similarity_symbol_policy()
    allow_unproven_buys = bool(settings.get("similarity_allow_unproven_buys", False))

    results: List[Dict[str, Any]] = []

    for quote in quotes[:max_symbols]:
        symbol = quote_symbol(quote)
        price = quote_price(quote)

        if not symbol or price <= 0:
            continue

        history_source = "none"

        try:
            historical, history_source = fetch_history_with_fallback(symbol, limit=history_limit)
        except Exception as exc:
            results.append({
                "engine_id": ENGINE_ID,
                "symbol": symbol,
                "decision": "AVOID",
                "score": 0.0,
                "price": price,
                "move_pct": quote_move_pct(quote),
                "spread_pct": quote_spread_pct(quote),
                "volume": quote_volume(quote),
                "source": "similarity_engine",
            "history_source": history_source,
                "reason": f"Similarity history fetch failed: {exc}",
                "similar_cases": 0,
                "prediction_horizon_days": 1,
            })
            continue

        if len(historical) < window + horizon_bars + min_cases:
            results.append({
                "engine_id": ENGINE_ID,
                "symbol": symbol,
                "decision": "AVOID",
                "score": 0.0,
                "price": price,
                "move_pct": quote_move_pct(quote),
                "spread_pct": quote_spread_pct(quote),
                "volume": quote_volume(quote),
                "source": "similarity_engine",
            "history_source": history_source,
                "reason": f"Not enough 5m history for similarity engine: {len(historical)} candles.",
                "similar_cases": 0,
                "prediction_horizon_days": 1,
            })
            continue

        current_history = build_current_pseudo_candle_history(quote, historical)
        current_features = build_pattern_features(current_history, window=window)

        if not current_features:
            continue

        similar_cases, outcomes = find_similar_cases(
            historical,
            current_features,
            window=window,
            horizon_bars=horizon_bars,
            max_cases_to_scan=max_cases_to_scan,
            top_k=top_k,
        )

        summary = summarize_similar_outcomes(outcomes)
        score = historical_similarity_score(summary, settings)

        # Visibility floor for testing: if real historical cases were found,
        # give AVOID rows a tiny score so they show above 0-score rows.
        # This does not make them buy candidates.
        if score <= 0 and int(summary.get("cases", 0)) > 0:
            score = 0.1

        decision = decision_from_score(score, settings)

        cases = int(summary.get("cases", 0))

        if cases < min_cases:
            decision = "AVOID"
            score = 0.0

        symbol_policy = policy_for_symbol(symbol, policy)

        original_decision = decision

        force_buy_score = safe_float(settings.get("similarity_force_buy_score"), 80.0)

        # Strong similarity override:
        # If the historical pattern score is very strong, allow the similarity
        # engine to become a real BUY_CANDIDATE even if policy would normally
        # downgrade it to WATCH. This is still paper trading only.
        force_similarity_buy = score >= force_buy_score

        if symbol_policy == "BLOCK_BUY" and not force_similarity_buy:
            if decision == "BUY_CANDIDATE":
                decision = "AVOID"

        elif symbol_policy == "WATCH_ONLY" and not force_similarity_buy:
            if decision == "BUY_CANDIDATE":
                decision = "WATCH"

        elif symbol_policy == "UNPROVEN" and not allow_unproven_buys and not force_similarity_buy:
            if decision == "BUY_CANDIDATE":
                decision = "WATCH"

        if force_similarity_buy:
            decision = "BUY_CANDIDATE"

        reason = (
            f"{cases} similar 5m patterns. "
            f"Win rate {summary.get('win_rate_pct', 0.0):.1f}%. "
            f"Avg forward {summary.get('avg_forward_return_pct', 0.0):.3f}%. "
            f"Avg max gain {summary.get('avg_max_gain_pct', 0.0):.3f}%. "
            f"Avg drawdown {summary.get('avg_max_drawdown_pct', 0.0):.3f}%."
        )

        results.append({
            "engine_id": ENGINE_ID,
            "symbol": symbol,
            "decision": decision,
            "score": score,
            "price": price,
            "move_pct": quote_move_pct(quote),
            "spread_pct": quote_spread_pct(quote),
            "volume": quote_volume(quote),
            "source": "similarity_engine",
            "history_source": history_source,
            "reason": reason + f" Policy={symbol_policy}. Original={original_decision}.",
            "similarity_policy": symbol_policy,
            "original_decision": original_decision,
            "similar_cases": cases,
            "similarity_win_rate_pct": round(summary.get("win_rate_pct", 0.0), 2),
            "similarity_avg_forward_return_pct": round(summary.get("avg_forward_return_pct", 0.0), 4),
            "similarity_avg_max_gain_pct": round(summary.get("avg_max_gain_pct", 0.0), 4),
            "similarity_avg_drawdown_pct": round(summary.get("avg_max_drawdown_pct", 0.0), 4),
            "prediction_horizon_days": 1,
        })

    results.sort(key=lambda r: float(r.get("score") or 0.0), reverse=True)
    return results







