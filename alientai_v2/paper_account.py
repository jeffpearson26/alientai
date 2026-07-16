from __future__ import annotations

from typing import Any, Dict, Optional

from alientai_v2.settings import load_settings
from alientai_v2.utils import DATA_DIR, load_json, now_iso, safe_float, save_json


ACCOUNT_FILE = DATA_DIR / "v2_paper_account.json"


def load_account() -> Dict[str, Any]:
    settings = load_settings()

    default = {
        "build": "ALIENTAI_V2_REFACTORED",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "cash": float(settings["starting_cash"]),
        "realized_pnl": 0.0,
        "open_positions": {},
        "closed_trades": [],
        "trade_log": [],
    }

    account = load_json(ACCOUNT_FILE, default)

    if not isinstance(account, dict):
        account = default

    for key, value in default.items():
        if key not in account:
            account[key] = value

    return account


def save_account(account: Dict[str, Any]) -> None:
    account["updated_at"] = now_iso()
    save_json(ACCOUNT_FILE, account)


def calculate_account_metrics(account: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    # The account file is the source of truth for its original balance.
    # This prevents later settings changes or cash deposits from creating
    # incorrect profit-and-loss calculations.
    starting_cash = safe_float(
        account.get(
            "starting_balance",
            account.get(
                "starting_cash",
                account.get(
                    "initial_cash",
                    settings.get("starting_cash", 20000.0),
                ),
            ),
        ),
        20000.0,
    )
    cash = safe_float(account.get("cash"), starting_cash)
    open_positions = account.get("open_positions", {})

    if not isinstance(open_positions, dict):
        open_positions = {}

    open_position_value = 0.0
    open_position_cost = 0.0
    unrealized_pnl = 0.0

    for pos in open_positions.values():
        if not isinstance(pos, dict):
            continue

        shares = safe_float(pos.get("shares"), 0.0)
        entry_price = safe_float(pos.get("entry_price"), 0.0)
        last_price = safe_float(pos.get("last_price"), entry_price)

        cost = shares * entry_price
        value = shares * last_price

        open_position_cost += cost
        open_position_value += value
        unrealized_pnl += value - cost

    realized_pnl = safe_float(account.get("realized_pnl"), 0.0)
    account_value = cash + open_position_value
    total_pnl = account_value - starting_cash
    total_pnl_pct = (total_pnl / starting_cash * 100.0) if starting_cash else 0.0

    return {
        "starting_cash": round(starting_cash, 2),
        "cash": round(cash, 2),
        "open_position_cost": round(open_position_cost, 2),
        "open_position_value": round(open_position_value, 2),
        "account_value": round(account_value, 2),
        "realized_pnl": round(realized_pnl, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 4),
    }


def buy_position(account: Dict[str, Any], candidate: Dict[str, Any], settings: Dict[str, Any], approval: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    symbol = str(candidate["symbol"]).upper()
    price = safe_float(candidate["price"], 0.0)

    if price <= 0:
        return None

    open_positions = account.setdefault("open_positions", {})

    if symbol in open_positions:
        return None

    if len(open_positions) >= int(settings.get("max_open_positions", 25)):
        return None

    small_position_dollars = safe_float(settings.get("small_position_dollars"), 500.0)
    max_single_share_price = safe_float(settings.get("max_single_share_price"), 2500.0)
    cash = safe_float(account.get("cash"), 0.0)

    if price > max_single_share_price:
        return None

    if cash < price:
        return None

    if approval and approval.get("approved"):
        shares = int(safe_float(approval.get("shares"), 0))
        cost = round(safe_float(approval.get("approved_dollars"), shares * price), 2)
    else:
        if price <= small_position_dollars:
            shares = int(small_position_dollars // price)
        else:
            shares = 1

        if shares < 1:
            shares = 1

        cost = round(shares * price, 2)

    if cost > cash:
        return None

    engine_id = str(candidate.get("engine_id") or "unknown_engine")
    prediction_horizon_minutes = safe_float(candidate.get("prediction_horizon_minutes"), 0.0)
    prediction_horizon_days = safe_float(
        candidate.get("prediction_horizon_days"),
        safe_float(settings.get("prediction_horizon_days"), 20.0),
    )

    if prediction_horizon_minutes <= 0:
        prediction_horizon_minutes = prediction_horizon_days * 24.0 * 60.0

    minimum_hold_minutes = safe_float(
        candidate.get("minimum_hold_minutes"),
        safe_float(settings.get("minimum_hold_minutes"), prediction_horizon_minutes),
    )

    position = {
        "symbol": symbol,
        "engine_id": engine_id,
        "side": "LONG",
        "shares": shares,
        "entry_price": price,
        "last_price": price,
        "highest_price": price,
        "entry_time": now_iso(),
        "entry_score": candidate["score"],
        "entry_reason": str(candidate.get("reason") or f"V2 entry with {prediction_horizon_days:g}-day prediction horizon"),
        "prediction_horizon_minutes": prediction_horizon_minutes,
        "prediction_horizon_days": prediction_horizon_days,
        "minimum_hold_minutes": minimum_hold_minutes,
        "scheduled_exit_time": candidate.get("scheduled_exit_time"),
        "exit_rule": candidate.get("exit_rule"),
        "allow_stop_before_min_hold": bool(settings.get("allow_stop_before_min_hold", False)),
        "allow_trailing_before_min_hold": bool(settings.get("allow_trailing_before_min_hold", False)),
        "allow_take_profit_before_min_hold": bool(settings.get("allow_take_profit_before_min_hold", False)),
        "cost": cost,
        "manager_approval_reason": approval.get("reason") if approval else "",
    }

    open_positions[symbol] = position
    account["cash"] = round(cash - cost, 2)

    trade = {
        "time": now_iso(),
        "action": "BUY",
        "symbol": symbol,
        "engine_id": engine_id,
        "shares": shares,
        "price": price,
        "value": cost,
        "reason": position["entry_reason"],
        "manager_approval_reason": approval.get("reason") if approval else "",
        "engine": "ALIENTAI_V2_REFACTORED",
    }

    account.setdefault("trade_log", []).append(trade)

    return trade


def sell_position(account: Dict[str, Any], symbol: str, price: float, reason: str) -> Optional[Dict[str, Any]]:
    symbol = str(symbol).upper()
    open_positions = account.setdefault("open_positions", {})

    if symbol not in open_positions:
        return None

    pos = open_positions.pop(symbol)

    shares = int(pos["shares"])
    entry_price = safe_float(pos["entry_price"], 0.0)

    value = round(shares * price, 2)
    cost = round(shares * entry_price, 2)
    pnl = round(value - cost, 2)
    pnl_pct = round(((price - entry_price) / entry_price) * 100.0, 2) if entry_price else 0.0

    account["cash"] = round(safe_float(account.get("cash"), 0.0) + value, 2)
    account["realized_pnl"] = round(safe_float(account.get("realized_pnl"), 0.0) + pnl, 2)

    trade = {
        "time": now_iso(),
        "action": "SELL",
        "symbol": symbol,
        "engine_id": pos.get("engine_id"),
        "shares": shares,
        "entry_price": entry_price,
        "exit_price": price,
        "value": value,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "reason": reason,
        "engine": "ALIENTAI_V2_REFACTORED",
    }

    account.setdefault("closed_trades", []).append(trade)
    account.setdefault("trade_log", []).append(trade)

    return trade




