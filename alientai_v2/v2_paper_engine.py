"""
AlientAI V2 Paper Engine

This is the new paper-trading runner.
The old scanner is NOT the trading brain here.

V2 goal:
- small positions
- more tickers
- simple early-entry logic
- paper-only safety
- visible status
- old scanner decisions ignored
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


BUILD = "ALIENTAI_V2_PAPER_ENGINE_DIRECT_RUNNER_V1"

BASE_DIR = Path(__file__).resolve().parent.parent
ACCOUNT_FILE = BASE_DIR / "v2_paper_account.json"
STATUS_FILE = BASE_DIR / "v2_status.json"
SETTINGS_FILE = BASE_DIR / "v2_settings.json"


DEFAULT_SETTINGS = {
    "v2_enabled": True,
    "paper_trading_enabled": True,

    "old_scanner_decision_making_enabled": False,

    "starting_cash": 10000.0,
    "max_position_dollars": 250.0,
    "max_open_positions": 25,
    "max_new_buys_per_scan": 6,

    "take_profit_pct": 3.0,
    "stop_loss_pct": -1.5,
    "trailing_stop_pct": 1.0,

    "scan_interval_seconds": 60,

    "watchlist": [
        "NVDA", "AMD", "AVGO", "TSM", "ASML", "ARM", "MU",
        "AMAT", "LRCX", "KLAC", "MRVL", "SMCI",
        "PLTR", "RIVN", "TSLA", "AAPL", "MSFT",
        "QQQ", "SPY", "IWM"
    ]
}


_engine_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_engine_lock = threading.Lock()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")



def minutes_since_iso(iso_text: Any) -> float:
    """
    Return how many minutes have passed since an ISO timestamp.
    If the timestamp is missing or invalid, return 0.
    """
    try:
        if not iso_text:
            return 0.0
        started = datetime.fromisoformat(str(iso_text))
        delta = datetime.now() - started
        return max(0.0, delta.total_seconds() / 60.0)
    except Exception:
        return 0.0
def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_settings() -> Dict[str, Any]:
    settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())
    changed = False

    for key, value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = value
            changed = True

    if changed or not SETTINGS_FILE.exists():
        save_json(SETTINGS_FILE, settings)

    return settings


def load_account() -> Dict[str, Any]:
    settings = load_settings()

    default_account = {
        "build": BUILD,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "cash": float(settings["starting_cash"]),
        "realized_pnl": 0.0,
        "open_positions": {},
        "closed_trades": [],
        "trade_log": [],
    }

    account = load_json(ACCOUNT_FILE, default_account)

    for key, value in default_account.items():
        if key not in account:
            account[key] = value

    return account


def save_account(account: Dict[str, Any]) -> None:
    account["updated_at"] = now_iso()
    save_json(ACCOUNT_FILE, account)



def calculate_v2_account_metrics(account: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate V2 paper account value and profit/loss.

    Account value means:
        cash + current market value of open positions

    Total P/L means:
        account value - starting cash

    Realized P/L comes from closed trades.
    Unrealized P/L comes from open positions.
    """

    starting_cash = safe_float(settings.get("starting_cash"), 10000.0)
    cash = safe_float(account.get("cash"), starting_cash)
    open_positions = account.get("open_positions", {})

    if not isinstance(open_positions, dict):
        open_positions = {}

    open_position_value = 0.0
    open_position_cost = 0.0
    unrealized_pnl = 0.0

    for symbol, pos in open_positions.items():
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
def save_status(extra: Dict[str, Any]) -> Dict[str, Any]:
    account = load_account()
    settings = load_settings()

    open_positions = account.get("open_positions", {})
    metrics = calculate_v2_account_metrics(account, settings)
    cash = metrics.get("cash", safe_float(account.get("cash"), 0.0))

    status = {
        "status": "success",
        "build": BUILD,
        "updated_at": now_iso(),
        "v2_engine_running": is_running(),
        "v2_enabled": settings.get("v2_enabled", True),
        "paper_trading_enabled": settings.get("paper_trading_enabled", True),
        "old_scanner_decision_making_enabled": False,
        "cash": round(cash, 2),
        "starting_cash": metrics.get("starting_cash"),
        "open_position_cost": metrics.get("open_position_cost"),
        "open_position_value": metrics.get("open_position_value"),
        "account_value": metrics.get("account_value"),
        "realized_pnl": metrics.get("realized_pnl"),
        "unrealized_pnl": metrics.get("unrealized_pnl"),
        "total_pnl": metrics.get("total_pnl"),
        "total_pnl_pct": metrics.get("total_pnl_pct"),
        "open_positions_count": len(open_positions),
        "open_positions": open_positions,
        "closed_trades_count": len(account.get("closed_trades", [])),
        "last_message": extra.get("last_message", ""),
        "last_action": extra.get("last_action", "WAIT"),
        "last_scan_time": extra.get("last_scan_time"),
        "watchlist": settings.get("watchlist", []),
        "note": "V2 is the active paper engine. Old scanner decision-making is disabled here.",
    }

    save_json(STATUS_FILE, status)
    return status


def get_status() -> Dict[str, Any]:
    if STATUS_FILE.exists():
        status = load_json(STATUS_FILE, {})
        if status:
            status["v2_engine_running"] = is_running()
            status["old_scanner_decision_making_enabled"] = False
            return status

    return save_status({
        "last_message": "V2 status created. Engine has not scanned yet.",
        "last_action": "WAIT",
        "last_scan_time": None,
    })


def is_running() -> bool:
    global _engine_thread
    return bool(_engine_thread and _engine_thread.is_alive() and not _stop_event.is_set())



def get_real_v2_quotes(symbols: List[str]) -> List[Dict[str, Any]]:
    """
    Load real Schwab quotes through the existing main.py Schwab quote pipe.

    Important:
    - V2 does NOT use the old scanner's decision logic.
    - V2 only borrows the quote-fetching function from main.py.
    - The buy/sell decisions remain inside this V2 engine.
    """

    import sys

    main_module = sys.modules.get("main")

    if main_module is None:
        main_module = sys.modules.get("__main__")

    if main_module is None:
        raise RuntimeError("Could not find loaded main module for Schwab quote access.")

    fetch_quotes_chunked = getattr(main_module, "fetch_quotes_chunked", None)
    quote_value = getattr(main_module, "quote_value", None)

    if fetch_quotes_chunked is None:
        raise RuntimeError("main.py fetch_quotes_chunked() was not found.")

    if quote_value is None:
        raise RuntimeError("main.py quote_value() was not found.")

    quote_result = fetch_quotes_chunked(symbols, chunk_size=100)

    if not isinstance(quote_result, dict):
        raise RuntimeError("Schwab quote result was not a dictionary.")

    if quote_result.get("status") not in {"success", "partial_success"}:
        raise RuntimeError(f"Schwab quotes failed: {quote_result}")

    raw_quotes = quote_result.get("quotes", {})

    if not isinstance(raw_quotes, dict):
        raise RuntimeError("Schwab quote payload did not contain a quotes dictionary.")

    cleaned_quotes: List[Dict[str, Any]] = []

    for symbol in symbols:
        raw = raw_quotes.get(symbol)

        if not isinstance(raw, dict):
            continue

        price = quote_value(
            raw,
            "mark",
            "lastPrice",
            "regularMarketLastPrice",
            "closePrice",
            default=0.0,
        )

        bid = quote_value(raw, "bidPrice", "bid", default=0.0)
        ask = quote_value(raw, "askPrice", "ask", default=0.0)
        close = quote_value(raw, "closePrice", "regularMarketPreviousClose", default=0.0)
        net_pct = quote_value(raw, "netPercentChange", "regularMarketPercentChange", default=0.0)
        volume = quote_value(raw, "totalVolume", "regularMarketTotalVolume", "volume", default=0.0)
        avg_volume = quote_value(raw, "averageVolume", "avg10DaysVolume", "avg1YearVolume", default=0.0)

        relative_volume = 1.0
        if avg_volume and avg_volume > 0:
            relative_volume = volume / avg_volume

        spread_percent = 99.0
        if bid > 0 and ask > 0 and ask >= bid:
            mid = (bid + ask) / 2.0
            if mid > 0:
                spread_percent = ((ask - bid) / mid) * 100.0
        elif price > 0:
            spread_percent = 0.25

        cleaned_quotes.append({
            "symbol": symbol,
            "price": round(float(price), 4),
            "net_change_percent": round(float(net_pct), 4),
            "relative_volume": round(float(relative_volume), 4),
            "spread_percent": round(float(spread_percent), 4),
            "volume": float(volume),
            "bid": float(bid),
            "ask": float(ask),
            "close": float(close),
            "source": "schwab_live_quote",
        })

    return cleaned_quotes

def fake_quote_for_boot_test(symbol: str, index: int) -> Dict[str, Any]:
    """
    This is a temporary boot-test quote.

    It lets us prove the V2 engine starts, loops, updates status,
    and can write paper account files.

    Next step after this boots:
    replace this with Schwab quote fetching from the existing project.
    """
    base = 100.0 + index
    drift = ((int(time.time()) // 60) % 10) * 0.05

    return {
        "symbol": symbol,
        "price": round(base + drift, 2),
        "net_change_percent": round(0.15 + (index % 5) * 0.08, 2),
        "relative_volume": round(1.2 + (index % 4) * 0.7, 2),
        "spread_percent": 0.08,
    }


def score_v2_candidate(quote: Dict[str, Any]) -> Dict[str, Any]:
    """
    V2 graduated scoring.

    This fixes the earlier problem where almost every strong mover tied at 70.
    The score now separates a +7% mover from a +1% mover.
    """

    symbol = str(quote.get("symbol") or "").upper()
    price = safe_float(quote.get("price"), 0.0)
    move = safe_float(quote.get("net_change_percent"), 0.0)
    rv = safe_float(quote.get("relative_volume"), 1.0)
    spread = safe_float(quote.get("spread_percent"), 99.0)
    volume = safe_float(quote.get("volume"), 0.0)

    reasons: List[str] = []
    warnings: List[str] = []

    score = 0.0

    if price <= 0:
        return {
            "symbol": symbol,
            "price": price,
            "score": 0.0,
            "move_pct": move,
            "relative_volume": rv,
            "spread_percent": spread,
            "volume": volume,
            "source": quote.get("source"),
            "decision": "BLOCK",
            "reasons": [],
            "warnings": ["Invalid or missing price."],
        }

    # Momentum score.
    # Positive movers get a base score, then a graduated bonus.
    if move > 0:
        score += 20
        reasons.append("Positive mover.")

        move_points = min(35.0, move * 5.0)
        score += move_points
        reasons.append(f"Move bonus: +{round(move_points, 2)} from {round(move, 3)}% move.")
    else:
        score -= 25
        warnings.append("Not a positive mover.")

    # Relative volume score.
    if rv >= 3.0:
        score += 20
        reasons.append("Very strong relative volume.")
    elif rv >= 2.0:
        score += 14
        reasons.append("Strong relative volume.")
    elif rv >= 1.5:
        score += 8
        reasons.append("Moderate relative volume.")
    elif rv > 1.05:
        score += 3
        reasons.append("Slightly elevated relative volume.")
    else:
        reasons.append("Relative volume neutral or unavailable.")

    # Raw volume score.
    if volume >= 10_000_000:
        score += 8
        reasons.append("Very liquid: volume over 10M.")
    elif volume >= 2_000_000:
        score += 5
        reasons.append("Liquid: volume over 2M.")
    elif volume >= 500_000:
        score += 2
        reasons.append("Usable volume.")
    elif volume > 0:
        score -= 5
        warnings.append("Low volume.")

    # Spread score.
    if spread <= 0.03:
        score += 12
        reasons.append("Excellent spread.")
    elif spread <= 0.10:
        score += 9
        reasons.append("Very tight spread.")
    elif spread <= 0.20:
        score += 5
        reasons.append("Acceptable spread.")
    elif spread <= 0.35:
        score += 1
        warnings.append("Spread is a little wide.")
    else:
        score -= 25
        warnings.append("Spread is too wide.")

    # Low-price risk penalty.
    if price < 2:
        score -= 30
        warnings.append("Sub-$2 price blocked/penalized.")
    elif price < 5:
        score -= 10
        warnings.append("Low-priced stock; extra noise risk.")

    score = max(0.0, min(100.0, score))

    if score >= 75:
        decision = "STRONG_BUY_CANDIDATE"
    elif score >= 55:
        decision = "BUY_CANDIDATE"
    elif score >= 40:
        decision = "WATCH"
    else:
        decision = "AVOID"

    return {
        "symbol": symbol,
        "price": round(price, 4),
        "score": round(score, 2),
        "move_pct": round(move, 4),
        "relative_volume": round(rv, 4),
        "spread_percent": round(spread, 4),
        "volume": volume,
        "source": quote.get("source"),
        "decision": decision,
        "reasons": reasons,
        "warnings": warnings,
    }

def buy_position(account: Dict[str, Any], candidate: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Buy a V2 paper position.

    Sizing rule:
    - If price is less than or equal to small_position_dollars, buy whole shares up to that small-position budget.
    - If price is greater than small_position_dollars but less than or equal to max_single_share_price, buy exactly 1 share.
    - If price is greater than max_single_share_price, skip.
    """

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

    if price <= small_position_dollars:
        shares = int(small_position_dollars // price)
    else:
        shares = 1

    if shares < 1:
        shares = 1

    cost = round(shares * price, 2)

    if cost > cash:
        return None

    prediction_horizon_days = safe_float(settings.get("prediction_horizon_days"), 20.0)
    minimum_hold_minutes = safe_float(settings.get("minimum_hold_minutes"), prediction_horizon_days * 24.0 * 60.0)

    position = {
        "symbol": symbol,
        "side": "LONG",
        "shares": shares,
        "entry_price": price,
        "last_price": price,
        "highest_price": price,
        "entry_time": now_iso(),
        "entry_score": candidate["score"],
        "entry_reason": f"V2 entry with {prediction_horizon_days:g}-day prediction horizon",
        "prediction_horizon_days": prediction_horizon_days,
        "minimum_hold_minutes": minimum_hold_minutes,
        "allow_stop_before_min_hold": bool(settings.get("allow_stop_before_min_hold", False)),
        "allow_trailing_before_min_hold": bool(settings.get("allow_trailing_before_min_hold", False)),
        "allow_take_profit_before_min_hold": bool(settings.get("allow_take_profit_before_min_hold", False)),
        "cost": cost,
    }

    open_positions[symbol] = position
    account["cash"] = round(cash - cost, 2)

    trade = {
        "time": now_iso(),
        "action": "BUY",
        "symbol": symbol,
        "shares": shares,
        "price": price,
        "value": cost,
        "reason": position["entry_reason"],
        "engine": BUILD,
    }

    account.setdefault("trade_log", []).append(trade)

    return trade

def sell_position(account: Dict[str, Any], symbol: str, price: float, reason: str) -> Optional[Dict[str, Any]]:
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
        "shares": shares,
        "entry_price": entry_price,
        "exit_price": price,
        "value": value,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "reason": reason,
        "engine": BUILD,
    }

    account.setdefault("closed_trades", []).append(trade)
    account.setdefault("trade_log", []).append(trade)

    return trade


def manage_open_positions(account: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Manage open V2 paper positions using real Schwab quotes.

    This keeps last_price, highest_price, unrealized P/L, trailing stop,
    and automatic sell rules updated from live Schwab data.
    """

    actions = []
    open_positions = account.setdefault("open_positions", {})

    if not open_positions:
        return actions

    take_profit_pct = safe_float(settings.get("take_profit_pct"), 3.0)
    stop_loss_pct = safe_float(settings.get("stop_loss_pct"), -1.5)
    trailing_stop_pct = safe_float(settings.get("trailing_stop_pct"), 1.0)
    max_hold_minutes = safe_float(settings.get("max_hold_minutes"), 90.0)

    symbols = list(open_positions.keys())
    live_quotes = get_real_v2_quotes(symbols)

    quote_by_symbol = {
        str(q.get("symbol", "")).upper(): q
        for q in live_quotes
        if isinstance(q, dict)
    }

    for symbol, pos in list(open_positions.items()):
        symbol = str(symbol).upper()
        quote = quote_by_symbol.get(symbol)

        if not quote:
            pos["last_quote_update_error"] = "No live Schwab quote returned for open position."
            continue

        entry_price = safe_float(pos.get("entry_price"), 0.0)
        new_price = safe_float(quote.get("price"), 0.0)

        if entry_price <= 0 or new_price <= 0:
            pos["last_quote_update_error"] = "Invalid entry price or live price."
            continue

        old_highest = safe_float(pos.get("highest_price"), entry_price)
        highest = max(old_highest, new_price)

        pos["last_price"] = round(new_price, 4)
        pos["highest_price"] = round(highest, 4)
        pos["last_quote_update"] = now_iso()
        pos["quote_source"] = quote.get("source", "schwab_live_quote")

        pnl_pct = ((new_price - entry_price) / entry_price) * 100.0
        trail_drop_pct = ((new_price - highest) / highest) * 100.0 if highest else 0.0

        pos["unrealized_pnl_pct"] = round(pnl_pct, 4)
        pos["trail_drop_pct"] = round(trail_drop_pct, 4)

        age_minutes = minutes_since_iso(pos.get("entry_time"))
        pos["age_minutes"] = round(age_minutes, 2)

        if max_hold_minutes > 0 and age_minutes >= max_hold_minutes:
            trade = sell_position(account, symbol, new_price, f"V2 max hold time exit after {round(age_minutes, 1)} minutes")
            if trade:
                actions.append(trade)

        elif pnl_pct >= take_profit_pct:
            trade = sell_position(account, symbol, new_price, "V2 Schwab quote take profit")
            if trade:
                actions.append(trade)

        elif pnl_pct <= stop_loss_pct:
            trade = sell_position(account, symbol, new_price, "V2 Schwab quote stop loss")
            if trade:
                actions.append(trade)

        elif trail_drop_pct <= -abs(trailing_stop_pct):
            trade = sell_position(account, symbol, new_price, "V2 Schwab quote trailing stop")
            if trade:
                actions.append(trade)

    return actions

def run_one_scan() -> Dict[str, Any]:
    settings = load_settings()
    account = load_account()

    if not settings.get("v2_enabled", True):
        status = save_status({
            "last_message": "V2 engine disabled in v2_settings.json.",
            "last_action": "WAIT",
            "last_scan_time": now_iso(),
        })
        return status

    sell_actions = manage_open_positions(account, settings)

    watchlist = settings.get("watchlist", [])
    quotes = get_real_v2_quotes(watchlist)
    scored = [score_v2_candidate(q) for q in quotes]
    scored.sort(key=lambda row: row["score"], reverse=True)

    buy_actions = []

    if settings.get("paper_trading_enabled", True):
        max_new = int(settings.get("max_new_buys_per_scan", 6))

        for candidate in scored:
            if len(buy_actions) >= max_new:
                break

            if candidate["decision"] not in {"BUY_CANDIDATE", "STRONG_BUY_CANDIDATE"}:
                continue

            trade = buy_position(account, candidate, settings)

            if trade:
                buy_actions.append(trade)

    save_account(account)

    if buy_actions:
        last_action = "BUY"
        message = f"V2 bought {len(buy_actions)} paper position(s)."
    elif sell_actions:
        last_action = "SELL"
        message = f"V2 sold {len(sell_actions)} paper position(s)."
    else:
        last_action = "WAIT"
        message = "V2 scanned. No new paper action."

    status = save_status({
        "last_message": message,
        "last_action": last_action,
        "last_scan_time": now_iso(),
    })

    status["top_v2_candidates"] = scored[:10]
    status["buy_actions"] = buy_actions
    status["sell_actions"] = sell_actions

    save_json(STATUS_FILE, status)

    return status


def engine_loop() -> None:
    settings = load_settings()
    interval = int(settings.get("scan_interval_seconds", 60))

    save_status({
        "last_message": "V2 engine loop started.",
        "last_action": "WAIT",
        "last_scan_time": None,
    })

    while not _stop_event.is_set():
        try:
            run_one_scan()
        except Exception as exc:
            save_status({
                "last_message": f"V2 engine error: {exc}",
                "last_action": "ERROR",
                "last_scan_time": now_iso(),
            })

        _stop_event.wait(interval)


def start_engine() -> Dict[str, Any]:
    global _engine_thread

    with _engine_lock:
        if is_running():
            return get_status()

        _stop_event.clear()
        _engine_thread = threading.Thread(target=engine_loop, daemon=True)
        _engine_thread.start()

    time.sleep(0.5)

    return get_status()


def stop_engine() -> Dict[str, Any]:
    _stop_event.set()

    return save_status({
        "last_message": "V2 engine stop requested.",
        "last_action": "STOP",
        "last_scan_time": now_iso(),
    })


def sell_all() -> Dict[str, Any]:
    account = load_account()
    open_positions = account.setdefault("open_positions", {})

    actions = []

    for symbol, pos in list(open_positions.items()):
        price = safe_float(pos.get("last_price"), pos.get("entry_price"))
        trade = sell_position(account, symbol, price, "V2 manual sell all")
        if trade:
            actions.append(trade)

    save_account(account)

    status = save_status({
        "last_message": f"V2 manual sell-all completed. Sold {len(actions)} position(s).",
        "last_action": "SELL_ALL",
        "last_scan_time": now_iso(),
    })

    status["sell_actions"] = actions
    save_json(STATUS_FILE, status)

    return status









