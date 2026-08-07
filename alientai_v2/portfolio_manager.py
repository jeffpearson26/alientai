from __future__ import annotations

from typing import Any, Dict, List, Optional

from alientai_v2.paper_account import calculate_account_metrics
from alientai_v2.utils import minutes_since_iso, safe_float


def candidate_strength_bucket(candidate: Dict[str, Any]) -> str:
    score = safe_float(candidate.get("score"), 0.0)

    if score >= 85:
        return "excellent"
    if score >= 75:
        return "strong"
    if score >= 65:
        return "good"
    if score >= 55:
        return "acceptable"

    return "weak"


def requested_dollars_for_candidate(candidate: Dict[str, Any], settings: Dict[str, Any]) -> float:
    """
    Let the manager size dynamically.

    The engine may request a size, but if it does not, the manager chooses
    based on engine type and score.
    """

    explicit = safe_float(candidate.get("requested_position_dollars"), 0.0)
    if explicit > 0:
        return explicit

    engine_id = str(candidate.get("engine_id") or "")
    score = safe_float(candidate.get("score"), 0.0)

    # Defaults.
    base = safe_float(settings.get("default_position_dollars"), 500.0)

    # Longer-term engines can use more capital because they are not quick scalp tests.
    if engine_id in {"prediction_20day", "ai_semi_20day"}:
        base = safe_float(settings.get("swing_position_dollars"), 750.0)

    if engine_id in {"momentum_5min"}:
        base = safe_float(settings.get("momentum_position_dollars"), 500.0)

    # Score-based adjustment.
    if score >= 85:
        return base * 1.75
    if score >= 75:
        return base * 1.35
    if score >= 65:
        return base * 1.0
    if score >= 55:
        return base * 0.75

    return 0.0


def approve_candidate_buy(
    *,
    account: Dict[str, Any],
    settings: Dict[str, Any],
    candidate: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Portfolio manager approval.

    Engines do not decide final size.
    They request a buy; the manager approves, resizes, or rejects it.
    """

    symbol = str(candidate.get("symbol") or "").upper()
    price = safe_float(candidate.get("price"), 0.0)
    decision = str(candidate.get("decision") or "")

    if decision not in {"BUY_CANDIDATE", "STRONG_BUY_CANDIDATE"}:
        return {
            "approved": False,
            "symbol": symbol,
            "reason": f"Candidate decision is {decision}, not buyable.",
        }

    if price <= 0:
        return {
            "approved": False,
            "symbol": symbol,
            "reason": "Invalid candidate price.",
        }

    open_positions = account.setdefault("open_positions", {})

    existing_position = open_positions.get(symbol)
    pyramid = False
    if isinstance(existing_position, dict):
        interval_seconds = max(
            300.0,
            safe_float(candidate.get("paper_pyramid_interval_seconds"), 300.0),
        )
        elapsed_minutes = minutes_since_iso(
            existing_position.get("last_add_time") or existing_position.get("entry_time")
        )
        pyramid = bool(
            candidate.get("paper_pyramid_allowed") is True
            and str(existing_position.get("engine_id") or "")
            == str(candidate.get("engine_id") or "")
            and elapsed_minutes * 60.0 >= interval_seconds
        )
        if not pyramid:
            return {
                "approved": False,
                "symbol": symbol,
                "reason": "Symbol is already open and no eligible five-minute uptrend add exists.",
            }

    max_open = int(settings.get("max_open_positions", 25))
    if len(open_positions) >= max_open:
        return {
            "approved": False,
            "symbol": symbol,
            "reason": f"Max open positions reached: {max_open}.",
        }

    metrics = calculate_account_metrics(account, settings)

    cash = safe_float(metrics.get("cash"), 0.0)
    invested = safe_float(
        metrics.get("total_invested_dollars"),
        safe_float(metrics.get("open_position_cost"), 0.0),
    )
    account_value = safe_float(metrics.get("account_value"), 0.0)

    target_invested = safe_float(settings.get("target_invested_dollars"), 9000.0)
    max_invested = safe_float(settings.get("max_invested_dollars"), 9000.0)
    target_cash = safe_float(settings.get("target_cash_reserve_dollars"), 1000.0)
    max_single_share_price = safe_float(settings.get("max_single_share_price"), 2500.0)

    if price > max_single_share_price:
        return {
            "approved": False,
            "symbol": symbol,
            "reason": f"Price {price} is above max single-share limit {max_single_share_price}.",
        }

    if cash < price:
        return {
            "approved": False,
            "symbol": symbol,
            "reason": f"Not enough cash for even 1 share. Cash {cash}, price {price}.",
            "needs_cash": True,
        }

    # How much room do we have before the max exposure cap?
    exposure_room = max(0.0, max_invested - invested)

    if exposure_room < price:
        return {
            "approved": False,
            "symbol": symbol,
            "reason": f"Exposure cap reached. Invested {invested}, max {max_invested}.",
            "needs_rotation": True,
        }

    requested_dollars = price if pyramid else requested_dollars_for_candidate(candidate, settings)

    if requested_dollars <= 0:
        return {
            "approved": False,
            "symbol": symbol,
            "reason": "Manager requested size is zero because candidate is too weak.",
        }

    # The manager wants to stay near target invested, not blindly preserve too much cash.
    dollars_to_use = min(requested_dollars, exposure_room, cash)

    # If we are already near/above target cash reserve, normal sizing is okay.
    # If buying would push cash below reserve, allow it only when still below target invested.
    projected_cash = cash - dollars_to_use
    under_target_invested = invested < target_invested

    if projected_cash < target_cash and not under_target_invested:
        dollars_to_use = max(0.0, cash - target_cash)

    # Whole-share sizing.
    if pyramid:
        shares = 1
    elif dollars_to_use >= price:
        shares = int(dollars_to_use // price)
    else:
        # If stock is expensive but allowed, buy exactly 1 share.
        shares = 1

    max_shares_per_trade = int(settings.get("max_shares_per_paper_trade", 0) or 0)
    if max_shares_per_trade > 0:
        shares = min(shares, max_shares_per_trade)

    if shares < 1:
        return {
            "approved": False,
            "symbol": symbol,
            "reason": "Manager sizing resulted in zero shares.",
        }

    cost = round(shares * price, 2)

    if cost > cash:
        return {
            "approved": False,
            "symbol": symbol,
            "reason": "Approved cost exceeds cash after sizing.",
        }

    if invested + cost > max_invested:
        return {
            "approved": False,
            "symbol": symbol,
            "reason": "Approved cost would exceed max invested limit.",
        }

    strength = candidate_strength_bucket(candidate)

    return {
        "approved": True,
        "symbol": symbol,
        "shares": shares,
        "approved_dollars": cost,
        "price": price,
        "engine_id": candidate.get("engine_id"),
        "pyramid": pyramid,
        "strength": strength,
        "reason": (
            f"Approved by portfolio manager. "
            f"Strength={strength}, pyramid={pyramid}, invested={round(invested, 2)}, "
            f"target={round(target_invested, 2)}, max={round(max_invested, 2)}."
        ),
        "portfolio_before": {
            "cash": cash,
            "invested": invested,
            "account_value": account_value,
            "target_invested": target_invested,
            "max_invested": max_invested,
            "target_cash": target_cash,
        },
    }


def rank_candidates_for_manager(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort candidates for manager review.

    Strong buy candidates first, then score, then longer-horizon candidates.
    """

    def key(row: Dict[str, Any]):
        decision_bonus = 1 if row.get("decision") == "STRONG_BUY_CANDIDATE" else 0
        score = safe_float(row.get("score"), 0.0)
        horizon = safe_float(row.get("prediction_horizon_minutes"), 0.0)
        return (decision_bonus, score, horizon)

    return sorted(candidates, key=key, reverse=True)
