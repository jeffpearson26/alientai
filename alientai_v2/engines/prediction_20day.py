from __future__ import annotations

from typing import Any, Dict, List

from alientai_v2.engines.base_engine import make_candidate
from alientai_v2.utils import safe_float


ENGINE_ID = "prediction_20day"



# --- V2 MASTER 20-DAY POLICY HELPERS ---
from pathlib import Path as _V2PolicyPath
import json as _v2_policy_json

_MASTER_POLICY_CACHE = None


def _v2_project_root_for_policy() -> _V2PolicyPath:
    # prediction_20day.py is:
    # project_root/alientai_v2/engines/prediction_20day.py
    return _V2PolicyPath(__file__).resolve().parents[2]


def _load_prediction_20day_master_policy() -> dict:
    global _MASTER_POLICY_CACHE

    if isinstance(_MASTER_POLICY_CACHE, dict):
        return _MASTER_POLICY_CACHE

    root = _v2_project_root_for_policy()

    master_path = (
        root
        / "data_v2"
        / "prediction_20day_daily_training"
        / "prediction_20day_master_symbol_policy.json"
    )

    old_path = (
        root
        / "data_v2"
        / "prediction_20day_daily_training"
        / "prediction_20day_symbol_policy.json"
    )

    raw = {}

    try:
        path_to_use = master_path if master_path.exists() else old_path
        if path_to_use.exists():
            raw = _v2_policy_json.loads(path_to_use.read_text(encoding="utf-8-sig"))
    except Exception:
        raw = {}

    if isinstance(raw, dict) and isinstance(raw.get("policy"), dict):
        raw_policy = raw.get("policy", {})
    elif isinstance(raw, dict):
        raw_policy = raw
    else:
        raw_policy = {}

    normalized = {}

    if isinstance(raw_policy, dict):
        for symbol, value in raw_policy.items():
            sym = str(symbol or "").upper().strip()
            if not sym:
                continue

            if isinstance(value, dict):
                info = dict(value)
                info["policy"] = str(info.get("policy") or "NO_DATA").upper()
                normalized[sym] = info
            else:
                normalized[sym] = {
                    "policy": str(value or "NO_DATA").upper()
                }

    _MASTER_POLICY_CACHE = normalized
    return normalized


def get_prediction_20day_master_policy(symbol: str) -> dict:
    symbol = str(symbol or "").upper().strip()
    policy_map = _load_prediction_20day_master_policy()

    value = policy_map.get(symbol)

    if isinstance(value, dict):
        return value

    return {"policy": "NO_DATA"}


def apply_prediction_20day_master_policy(symbol: str, decision: str, score: float, reason: str):
    policy_info = get_prediction_20day_master_policy(symbol)
    policy = str(policy_info.get("policy", "NO_DATA")).upper()

    decision = str(decision or "AVOID").upper()
    score = float(score or 0.0)
    reason = str(reason or "")

    buy_like = {"BUY_CANDIDATE", "STRONG_BUY_CANDIDATE"}

    if policy in {"BLOCK_BUY", "NO_DATA"}:
        if decision in buy_like:
            decision = "AVOID" if policy == "BLOCK_BUY" else "WATCH"
        score = min(score, 39.0)
        reason += f" Master20dPolicy={policy}: buy blocked."

    elif policy == "WATCH_ONLY":
        if decision in buy_like:
            decision = "WATCH"
        score = min(score, 49.0)
        reason += " Master20dPolicy=WATCH_ONLY: watch only."

    elif policy == "ALLOW_SMALL":
        if score >= 45.0:
            decision = "BUY_CANDIDATE"
        else:
            decision = "WATCH"
        score = max(score, 55.0)
        reason += " Master20dPolicy=ALLOW_SMALL: tiny paper position only."

    elif policy == "ALLOW_BUY":
        if score >= 45.0:
            decision = "BUY_CANDIDATE"
        score = max(score, 55.0)
        reason += " Master20dPolicy=ALLOW_BUY."

    elif policy == "ALLOW_BUY_STRONG":
        if score >= 40.0:
            decision = "BUY_CANDIDATE"
        score = max(score, 62.0)
        reason += " Master20dPolicy=ALLOW_BUY_STRONG."

    else:
        reason += f" Master20dPolicy={policy}."

    return decision, score, reason, policy_info
# --- END V2 MASTER 20-DAY POLICY HELPERS ---


def scan(quotes: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    20-day prediction engine.

    Purpose:
    - Longer-horizon swing/prediction candidates.
    - Minimum hold is 20 days by default.
    - The account/position manager should block stop loss, trailing stop,
      and take profit before the minimum hold completes.

    Current version:
    - Uses live quote strength as a first placeholder.
    - Later this should use daily candles, trend, sector strength, ML output,
      earnings calendar, and market regime.
    """

    candidates: List[Dict[str, Any]] = []

    horizon_days = safe_float(settings.get("prediction_20day_horizon_days"), 20.0)
    horizon_minutes = horizon_days * 24.0 * 60.0
    minimum_hold_minutes = safe_float(
        settings.get("prediction_20day_minimum_hold_minutes"),
        horizon_minutes,
    )

    ai_semi_symbols = {
        "NVDA", "AMD", "AVGO", "TSM", "ASML", "ARM", "MU",
        "AMAT", "LRCX", "KLAC", "MRVL", "SMCI", "PLTR",
    }

    for quote in quotes:
        symbol = str(quote.get("symbol") or quote.get("ticker") or quote.get("key") or "").upper().strip()

        # Do not allow blank-symbol rows into the candidate table.
        # A blank symbol row becomes a confusing dashboard line like:
        # prediction_20day AVOID 0.0 $0.00
        if not symbol:
            continue

        price = safe_float(quote.get("price"), 0.0)
        move = safe_float(quote.get("net_change_percent"), 0.0)
        rv = safe_float(quote.get("relative_volume"), 1.0)
        spread = safe_float(quote.get("spread_percent"), 99.0)
        volume = safe_float(quote.get("volume"), 0.0)

        if price <= 0:
            continue

        score = 0.0
        reasons: List[str] = []
        warnings: List[str] = []

        # Longer-horizon placeholder logic.
        # This should eventually be replaced with daily candle trend,
        # market regime, sector strength, and trained model output.
        if move >= 5.0:
            score += 38
            reasons.append("Very strong same-day move; possible multi-day momentum.")
        elif move >= 3.0:
            score += 30
            reasons.append("Strong same-day move.")
        elif move >= 1.5:
            score += 22
            reasons.append("Moderate positive move.")
        elif move > 0:
            score += 12
            reasons.append("Slight positive move.")
        else:
            score -= 20
            warnings.append("Not positive today.")

        if volume >= 20_000_000:
            score += 15
            reasons.append("Very strong liquidity.")
        elif volume >= 5_000_000:
            score += 10
            reasons.append("Good liquidity.")
        elif volume >= 1_000_000:
            score += 5
            reasons.append("Usable liquidity.")
        elif volume > 0:
            score -= 5
            warnings.append("Thin volume for 20-day prediction.")

        if rv >= 2.0:
            score += 12
            reasons.append("Relative volume confirms unusual interest.")
        elif rv >= 1.25:
            score += 5
            reasons.append("Some relative-volume confirmation.")
        else:
            reasons.append("Relative volume neutral or unavailable.")

        if spread <= 0.10:
            score += 10
            reasons.append("Spread is tight enough for entry.")
        elif spread <= 0.25:
            score += 4
            reasons.append("Spread acceptable.")
        else:
            score -= 15
            warnings.append("Spread is wide for entry.")

        if symbol in ai_semi_symbols:
            score += 8
            reasons.append("AI/semi universe preference.")

        score = max(0.0, min(100.0, score))

        if score >= 72:
            decision = "STRONG_BUY_CANDIDATE"
        elif score >= 55:
            decision = "BUY_CANDIDATE"
        elif score >= 40:
            decision = "WATCH"
        else:
            decision = "AVOID"

        reason = "; ".join(reasons) if reasons else f"20-day prediction candidate from {ENGINE_ID}."

        # Apply master 20-day policy.
        #
        # This gates the live placeholder score using the daily walk-forward
        # policy we trained from historical 1-day candles.
        #
        # Example:
        #   ALLOW_BUY_STRONG -> can become BUY_CANDIDATE
        #   ALLOW_BUY        -> can become BUY_CANDIDATE
        #   ALLOW_SMALL      -> can become BUY_CANDIDATE, but marked tiny
        #   WATCH_ONLY       -> visible but not buyable
        #   BLOCK_BUY        -> blocked
        #   NO_DATA          -> blocked unless we explicitly change that later
        decision, score, reason, master_policy_info = apply_prediction_20day_master_policy(
            symbol=symbol,
            decision=decision,
            score=score,
            reason=reason,
        )

        candidates.append(
            make_candidate(
                engine_id=ENGINE_ID,
                symbol=symbol,
                side="LONG",
                score=score,
                decision=decision,
                price=price,
                prediction_horizon_minutes=horizon_minutes,
                minimum_hold_minutes=minimum_hold_minutes,
                reason=reason,
                quote=quote,
                warnings=warnings,
                reasons=reasons + [
                    f"Master 20-day policy: {master_policy_info.get('policy')}",
                    f"Master buy win rate: {master_policy_info.get('buy_candidate_win_rate_pct')}",
                    f"Master avg buy return: {master_policy_info.get('avg_buy_future_20d_return_pct')}",
                    f"Master records: {master_policy_info.get('records')}",
                    f"Master buy candidates: {master_policy_info.get('buy_candidates')}",
                ],
            )
        )

    candidates.sort(key=lambda row: row.get("score", 0), reverse=True)
    return candidates
