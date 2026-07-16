from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


BUILD = "ALIENTAI_V2_OPTIONS_PAPER_ACCOUNT_V1"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data_v2"
ACCOUNT_PATH = DATA_DIR / "v2_options_paper_account.json"


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def load_account() -> Dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if ACCOUNT_PATH.exists():
        try:
            account = json.loads(ACCOUNT_PATH.read_text(encoding="utf-8-sig"))
            if isinstance(account, dict):
                return account
        except Exception:
            pass

    account = {
        "build": BUILD,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "starting_balance": 1000.0,
        "cash": 1000.0,
        "realized_pnl": 0.0,
        "open_option_positions": {},
        "closed_option_trades": [],
        "actions": [],
        "note": "Separate options paper account. This does not place real trades.",
    }

    save_account(account)
    return account


def save_account(account: Dict[str, Any]) -> Dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    account["updated_at"] = now_iso()
    ACCOUNT_PATH.write_text(json.dumps(account, indent=2), encoding="utf-8")
    return account


def option_position_key(row: Dict[str, Any]) -> str:
    option_symbol = str(row.get("option_contract_symbol") or row.get("option_symbol") or "").strip()
    return option_symbol


def estimated_contract_cost(row: Dict[str, Any]) -> float:
    cost = safe_float(row.get("estimated_contract_cost"), 0.0)
    if cost > 0:
        return cost

    mark = safe_float(row.get("mark") or row.get("price"), 0.0)
    return mark * 100.0


def can_buy_option(row: Dict[str, Any], settings: Dict[str, Any], account: Dict[str, Any]) -> tuple[bool, str]:
    if not bool(settings.get("options_paper_trading_enabled", False)):
        return False, "Options paper trading disabled."

    if bool(settings.get("options_live_trading_enabled", False)):
        return False, "Refusing: options live trading flag should stay false."

    if str(row.get("engine_id")) != "options_research":
        return False, "Not an options_research row."

    if str(row.get("decision")) != "OPTIONS_RESEARCH_PASS":
        return False, "Options row is not OPTIONS_RESEARCH_PASS."

    if not bool(row.get("research_pass")):
        return False, "Options row did not pass research filter."

    option_symbol = option_position_key(row)
    if not option_symbol:
        return False, "Missing option contract symbol."

    open_positions = account.setdefault("open_option_positions", {})
    if option_symbol in open_positions:
        return False, f"Already holding option contract {option_symbol}."

    max_position_cost = safe_float(settings.get("options_paper_max_position_cost"), 250.0)
    cost = estimated_contract_cost(row)

    if cost <= 0:
        return False, "Invalid option cost."

    if cost > max_position_cost:
        return False, f"Option cost ${cost:.2f} exceeds max position cost ${max_position_cost:.2f}."

    cash = safe_float(account.get("cash"), 0.0)
    if cost > cash:
        return False, f"Not enough options paper cash. Need ${cost:.2f}, have ${cash:.2f}."

    max_open = safe_int(settings.get("options_paper_max_open_positions"), 5)
    if max_open > 0 and len(open_positions) >= max_open:
        return False, f"Options paper max open positions reached: {max_open}."

    underlying = str(row.get("underlying_symbol") or row.get("symbol") or "").upper().strip()
    max_per_underlying = safe_int(settings.get("options_paper_max_positions_per_underlying"), 1)

    if max_per_underlying > 0:
        existing_same_underlying = 0
        for pos in open_positions.values():
            if str(pos.get("underlying_symbol") or "").upper().strip() == underlying:
                existing_same_underlying += 1

        if existing_same_underlying >= max_per_underlying:
            return False, f"Already holding max options for underlying {underlying}."

    return True, "Approved options paper buy."


def paper_buy_option(row: Dict[str, Any], settings: Dict[str, Any], account: Dict[str, Any]) -> Dict[str, Any]:
    ok, reason = can_buy_option(row, settings, account)

    if not ok:
        return {
            "action": "NO_BUY",
            "symbol": row.get("underlying_symbol") or row.get("symbol"),
            "option_contract_symbol": row.get("option_contract_symbol") or row.get("option_symbol"),
            "reason": reason,
        }

    option_symbol = option_position_key(row)
    contracts = 1
    mark = safe_float(row.get("mark") or row.get("price"), 0.0)
    cost = estimated_contract_cost(row)

    account["cash"] = safe_float(account.get("cash"), 0.0) - cost

    position = {
        "opened_at": now_iso(),
        "engine_id": "options_research",
        "underlying_symbol": row.get("underlying_symbol") or row.get("symbol"),
        "option_contract_symbol": option_symbol,
        "contract_type": row.get("contract_type", "CALL"),
        "side": "LONG_CALL",
        "contracts": contracts,
        "entry_mark": mark,
        "last_mark": mark,
        "entry_cost": cost,
        "last_value": cost,
        "expiration": row.get("expiration"),
        "dte_at_entry": row.get("dte"),
        "strike": row.get("strike"),
        "delta_at_entry": row.get("delta"),
        "spread_pct_at_entry": row.get("spread_pct"),
        "open_interest_at_entry": row.get("open_interest"),
        "research_score_at_entry": row.get("research_score") or row.get("score"),
        "entry_reason": row.get("reason"),
        "status": "OPEN",
    }

    open_positions = account.setdefault("open_option_positions", {})
    open_positions[option_symbol] = position

    action = {
        "time": now_iso(),
        "action": "BUY_OPTION_PAPER",
        "underlying_symbol": position["underlying_symbol"],
        "option_contract_symbol": option_symbol,
        "contracts": contracts,
        "mark": mark,
        "cost": cost,
        "reason": reason,
        "research_score": position["research_score_at_entry"],
    }

    actions = account.setdefault("actions", [])
    if isinstance(actions, list):
        actions.append(action)

    save_account(account)

    return action


def mark_open_positions_from_rows(account: Dict[str, Any], option_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    open_positions = account.setdefault("open_option_positions", {})
    row_by_contract = {}

    for row in option_rows:
        key = option_position_key(row)
        if key:
            row_by_contract[key] = row

    total_open_value = 0.0
    total_unrealized = 0.0

    for option_symbol, pos in open_positions.items():
        row = row_by_contract.get(option_symbol)

        if row:
            mark = safe_float(row.get("mark") or row.get("price"), safe_float(pos.get("last_mark"), 0.0))
            value = mark * 100.0 * safe_float(pos.get("contracts"), 1.0)

            pos["last_mark"] = mark
            pos["last_value"] = value
            pos["last_update"] = now_iso()
            pos["current_dte"] = row.get("dte")
            pos["current_delta"] = row.get("delta")
            pos["current_spread_pct"] = row.get("spread_pct")
        else:
            value = safe_float(pos.get("last_value"), safe_float(pos.get("entry_cost"), 0.0))

        entry_cost = safe_float(pos.get("entry_cost"), 0.0)
        unrealized = value - entry_cost
        pos["unrealized_pnl"] = unrealized
        pos["unrealized_pnl_pct"] = (unrealized / entry_cost * 100.0) if entry_cost > 0 else 0.0

        total_open_value += value
        total_unrealized += unrealized

    account["open_option_value"] = total_open_value
    account["unrealized_pnl"] = total_unrealized
    account["account_value"] = safe_float(account.get("cash"), 0.0) + total_open_value
    account["total_pnl"] = account["account_value"] - safe_float(account.get("starting_balance"), 1000.0)
    account["total_pnl_pct"] = (
        account["total_pnl"] / safe_float(account.get("starting_balance"), 1000.0) * 100.0
        if safe_float(account.get("starting_balance"), 1000.0) > 0
        else 0.0
    )

    save_account(account)
    return account


def maybe_buy_from_research_rows(option_rows: List[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:
    account = load_account()

    # Mark current open positions first.
    account = mark_open_positions_from_rows(account, option_rows)

    actions: List[Dict[str, Any]] = []

    if not bool(settings.get("options_paper_trading_enabled", False)):
        return {
            "status": "disabled",
            "message": "Options paper trading disabled.",
            "account": account,
            "actions": actions,
        }

    max_buys_per_scan = safe_int(settings.get("options_paper_max_buys_per_scan"), 1)

    ranked = sorted(
        [r for r in option_rows if str(r.get("decision")) == "OPTIONS_RESEARCH_PASS"],
        key=lambda r: safe_float(r.get("score") or r.get("research_score"), 0.0),
        reverse=True,
    )

    for row in ranked:
        if max_buys_per_scan > 0 and len([a for a in actions if a.get("action") == "BUY_OPTION_PAPER"]) >= max_buys_per_scan:
            break

        action = paper_buy_option(row, settings, account)
        actions.append(action)

        # Reload account after a buy.
        account = load_account()

    account = mark_open_positions_from_rows(account, option_rows)

    return {
        "status": "success",
        "message": "Options paper manager completed.",
        "account": account,
        "actions": actions,
    }
