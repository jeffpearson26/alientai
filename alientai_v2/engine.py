from __future__ import annotations

import threading
import time
from datetime import datetime, time as datetime_time
from zoneinfo import ZoneInfo
from typing import Any, Dict, List

from alientai_v2.portfolio_manager import approve_candidate_buy, rank_candidates_for_manager
from alientai_v2.paper_account import (
    buy_position,
    calculate_account_metrics,
    load_account,
    save_account,
    sell_position,
)
from alientai_v2.engines.engine_registry import run_enabled_engines
from alientai_v2.engines.contextual_options_paper import candidate_symbols as contextual_candidate_symbols
from alientai_v2.engines.nasdaq100_technical_paper import candidate_symbols as nasdaq100_candidate_symbols
from alientai_v2.alpha_vantage_quote_client import get_real_v2_quotes
from alientai_v2.settings import load_settings
from alientai_v2.options_paper import maybe_buy_from_research_rows
from alientai_v2.shadow_signals import record_shadow_signals
from alientai_v2.shadow_outcomes import evaluate_due_shadow_signals
from alientai_v2.shadow_scorecard import build_shadow_engine_scorecard
from alientai_v2.utils import DATA_DIR, load_json, minutes_since_iso, now_iso, safe_float, save_json


BUILD = "ALIENTAI_V2_REFACTORED_CLEAN_APP_V1"

STATUS_FILE = DATA_DIR / "v2_status.json"

_engine_thread = None
_stop_event = threading.Event()
_engine_lock = threading.Lock()


def is_running() -> bool:
    global _engine_thread
    return bool(_engine_thread and _engine_thread.is_alive() and not _stop_event.is_set())


def paper_buys_on_market_day(
    account: Dict[str, Any], settings: Dict[str, Any], market_day: str | None = None,
) -> int:
    """Count completed paper BUY actions for one configured local market day."""
    if market_day is None:
        timezone = ZoneInfo(str(settings.get("timezone") or "America/Los_Angeles"))
        market_day = datetime.now(timezone).date().isoformat()
    trade_log = account.get("trade_log", [])
    if not isinstance(trade_log, list):
        return 0
    return sum(
        1 for trade in trade_log
        if isinstance(trade, dict)
        and str(trade.get("action") or "").upper() == "BUY"
        and str(trade.get("time") or "")[:10] == market_day
    )


def save_status(extra: Dict[str, Any]) -> Dict[str, Any]:
    account = load_account()
    settings = load_settings()
    open_positions = account.get("open_positions", {})
    if not isinstance(open_positions, dict):
        open_positions = {}

    metrics = calculate_account_metrics(account, settings)
    buys_today = paper_buys_on_market_day(account, settings)
    daily_limit = max(0, int(settings.get("max_new_buys_per_day", 5)))

    status = {
        "status": "success",
        "build": BUILD,
        "updated_at": now_iso(),
        "v2_engine_running": is_running(),
        "v2_enabled": settings.get("v2_enabled", True),
        "paper_trading_enabled": settings.get("paper_trading_enabled", True),
        "old_scanner_decision_making_enabled": False,
        "enabled_engines": settings.get("enabled_engines", []),
        "paper_buys_today": buys_today,
        "max_new_buys_per_day": daily_limit,
        "paper_buys_remaining_today": max(0, daily_limit - buys_today),

        **metrics,

        "open_positions_count": len(open_positions),
        "open_positions": open_positions,
        "closed_trades_count": len(account.get("closed_trades", [])),
        "last_message": extra.get("last_message", ""),
        "last_action": extra.get("last_action", "WAIT"),
        "last_scan_time": extra.get("last_scan_time"),
        "watchlist": settings.get("watchlist", []),
        "top_v2_candidates": extra.get("top_v2_candidates", []),
        "buy_actions": extra.get("buy_actions", []),
        "sell_actions": extra.get("sell_actions", []),
        "buy_window": extra.get("buy_window", {}),
        "note": "Clean V2 app. Old scanner decision-making is not loaded.",
    }

    save_json(STATUS_FILE, status)
    return status


def get_status() -> Dict[str, Any]:
    """
    Return current V2 status with freshly calculated account metrics.

    The saved status file is used only to preserve descriptive information
    such as the last scan message, candidates, and actions. Financial values
    are always recalculated from the live paper-account file.
    """
    saved_status = {}

    if STATUS_FILE.exists():
        loaded = load_json(STATUS_FILE, {})
        if isinstance(loaded, dict):
            saved_status = loaded

    refreshed = save_status({
        "last_message": saved_status.get("last_message", "V2 status created."),
        "last_action": saved_status.get("last_action", "WAIT"),
        "last_scan_time": saved_status.get("last_scan_time"),
        "top_v2_candidates": saved_status.get("top_v2_candidates", []),
        "buy_actions": saved_status.get("buy_actions", []),
        "sell_actions": saved_status.get("sell_actions", []),
        "buy_window": saved_status.get("buy_window", {}),
    })

    refreshed["v2_engine_running"] = is_running()
    refreshed["old_scanner_decision_making_enabled"] = False
    return refreshed


def symbol_stop_cooldown_reason(
    account: Dict[str, Any],
    symbol: str,
    settings: Dict[str, Any],
) -> str:
    """Return a rejection reason when a symbol was recently sold by a stop."""
    if not bool(settings.get("stop_reentry_cooldown_enabled", True)):
        return ""

    cooldown_hours = max(
        0.0,
        safe_float(settings.get("stop_reentry_cooldown_hours"), 168.0),
    )
    if cooldown_hours <= 0:
        return ""

    normalized_symbol = str(symbol or "").upper().strip()
    closed_trades = account.get("closed_trades", [])
    if not isinstance(closed_trades, list):
        return ""

    for trade in reversed(closed_trades):
        if not isinstance(trade, dict):
            continue
        if str(trade.get("symbol") or "").upper().strip() != normalized_symbol:
            continue

        reason = str(trade.get("reason") or "").lower()
        if "stop" not in reason:
            continue

        age_minutes = minutes_since_iso(str(trade.get("time") or ""))
        if age_minutes is None:
            continue
        if 0.0 <= age_minutes < cooldown_hours * 60.0:
            remaining = max(0.0, cooldown_hours - age_minutes / 60.0)
            return (
                f"Stop re-entry cooldown active for {normalized_symbol}: "
                f"{remaining:.1f} hour(s) remaining."
            )
        break

    return ""


def engine_main_buying_rejection(
    candidate: Dict[str, Any],
    settings: Dict[str, Any],
) -> str:
    """Reject main-account buys unless the candidate engine is allowlisted."""
    engine_id = str(candidate.get("engine_id") or "").strip()
    configured = settings.get("main_account_enabled_buy_engines", [])
    if not isinstance(configured, list):
        configured = []
    allowed = {str(value).strip() for value in configured if str(value).strip()}
    if engine_id not in allowed:
        return (
            f"Main-account buying disabled for engine {engine_id or 'unknown_engine'}. "
            "Engine is research-only until explicitly allowlisted."
        )
    return ""


def manage_open_positions(account: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    open_positions = account.setdefault("open_positions", {})

    if not open_positions:
        return actions

    take_profit_pct = safe_float(settings.get("take_profit_pct"), 3.0)
    stop_loss_pct = safe_float(settings.get("stop_loss_pct"), -1.5)
    trailing_stop_pct = safe_float(settings.get("trailing_stop_pct"), 1.0)
    trailing_stop_activation_pct = safe_float(settings.get("trailing_stop_activation_pct"), 1.0)
    emergency_stop_enabled = bool(settings.get("emergency_stop_enabled", True))
    default_emergency_stop_loss_pct = safe_float(settings.get("emergency_stop_loss_pct"), -5.0)

    default_prediction_horizon_days = safe_float(settings.get("prediction_horizon_days"), 20.0)
    default_minimum_hold_minutes = safe_float(
        settings.get("minimum_hold_minutes"),
        default_prediction_horizon_days * 24.0 * 60.0,
    )
    max_hold_minutes = safe_float(settings.get("max_hold_minutes"), default_minimum_hold_minutes)

    symbols = list(open_positions.keys())
    live_quotes = get_real_v2_quotes(symbols)
    quote_by_symbol = {str(q.get("symbol", "")).upper(): q for q in live_quotes if isinstance(q, dict)}

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
        pos["quote_source"] = quote.get("source", "alpha_vantage_realtime_bulk_quote")

        pnl_pct = ((new_price - entry_price) / entry_price) * 100.0
        trail_drop_pct = ((new_price - highest) / highest) * 100.0 if highest else 0.0
        age_minutes = minutes_since_iso(pos.get("entry_time"))

        prediction_horizon_days = safe_float(pos.get("prediction_horizon_days"), default_prediction_horizon_days)
        minimum_hold_minutes = safe_float(pos.get("minimum_hold_minutes"), default_minimum_hold_minutes)

        scheduled_exit_time = str(pos.get("scheduled_exit_time") or "").strip()
        scheduled_exit_reached = False

        if scheduled_exit_time:
            try:
                scheduled_exit_dt = datetime.fromisoformat(scheduled_exit_time)
                now_pacific = datetime.now(ZoneInfo("America/Los_Angeles"))

                if scheduled_exit_dt.tzinfo is None:
                    scheduled_exit_dt = scheduled_exit_dt.replace(
                        tzinfo=ZoneInfo("America/Los_Angeles")
                    )

                scheduled_exit_reached = now_pacific >= scheduled_exit_dt
            except Exception as exc:
                pos["scheduled_exit_error"] = str(exc)

        min_hold_complete = (
            scheduled_exit_reached
            if pos.get("exit_rule") == "friday_noon_pacific"
            else age_minutes >= minimum_hold_minutes
        )

        pos["unrealized_pnl_pct"] = round(pnl_pct, 4)
        pos["trail_drop_pct"] = round(trail_drop_pct, 4)
        pos["age_minutes"] = round(age_minutes, 2)
        pos["prediction_horizon_days"] = prediction_horizon_days
        pos["minimum_hold_minutes"] = minimum_hold_minutes
        pos["min_hold_complete"] = min_hold_complete
        pos["minutes_until_sell_allowed"] = round(max(0.0, minimum_hold_minutes - age_minutes), 2)

        allow_stop_before = bool(pos.get("allow_stop_before_min_hold", settings.get("allow_stop_before_min_hold", False)))
        allow_trailing_before = bool(pos.get("allow_trailing_before_min_hold", settings.get("allow_trailing_before_min_hold", False)))
        allow_take_profit_before = bool(pos.get("allow_take_profit_before_min_hold", settings.get("allow_take_profit_before_min_hold", False)))
        position_emergency_stop_enabled = bool(
            pos.get("emergency_stop_enabled", emergency_stop_enabled)
        )
        emergency_stop_loss_pct = safe_float(
            pos.get("emergency_stop_loss_pct"),
            default_emergency_stop_loss_pct,
        )

        # The prediction horizon controls the planned hold, not the maximum
        # acceptable loss. This hard stop is intentionally evaluated before
        # scheduled/minimum-hold gates so a losing position cannot be trapped.
        if (
            position_emergency_stop_enabled
            and emergency_stop_loss_pct < 0.0
            and pnl_pct <= emergency_stop_loss_pct
        ):
            trade = sell_position(
                account,
                symbol,
                new_price,
                f"V2 emergency stop at {round(pnl_pct, 2)}% (limit {emergency_stop_loss_pct}%)",
            )
            if trade:
                actions.append(trade)
            continue

        if pos.get("exit_rule") == "friday_noon_pacific" and scheduled_exit_reached:
            trade = sell_position(
                account,
                symbol,
                new_price,
                f"Friday engine scheduled exit reached: {scheduled_exit_time}",
            )
            if trade:
                actions.append(trade)
            continue

        if not min_hold_complete:
            blocked = []

            if pnl_pct <= stop_loss_pct and not allow_stop_before:
                blocked.append("stop loss blocked before minimum hold")

            if pnl_pct >= take_profit_pct and not allow_take_profit_before:
                blocked.append("take profit blocked before minimum hold")

            if pnl_pct >= trailing_stop_activation_pct and trail_drop_pct <= -abs(trailing_stop_pct) and not allow_trailing_before:
                blocked.append("trailing stop blocked before minimum hold")

            if blocked:
                pos["last_sell_blocked_reason"] = "; ".join(blocked)
            else:
                pos["last_sell_blocked_reason"] = f"Minimum hold active: {round(pos['minutes_until_sell_allowed'], 1)} minutes remaining."

            continue

        if max_hold_minutes > 0 and age_minutes >= max_hold_minutes:
            trade = sell_position(account, symbol, new_price, f"V2 max hold exit after {round(age_minutes, 1)} minutes")
            if trade:
                actions.append(trade)

        elif pnl_pct >= take_profit_pct:
            trade = sell_position(account, symbol, new_price, "V2 take profit after minimum hold")
            if trade:
                actions.append(trade)

        elif pnl_pct <= stop_loss_pct:
            trade = sell_position(account, symbol, new_price, "V2 stop loss after minimum hold")
            if trade:
                actions.append(trade)

        elif pnl_pct >= trailing_stop_activation_pct and trail_drop_pct <= -abs(trailing_stop_pct):
            trade = sell_position(account, symbol, new_price, "V2 trailing stop after minimum hold")
            if trade:
                actions.append(trade)

    return actions



def market_buy_window_status(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decide whether V2 is allowed to open NEW paper buys right now.

    V2 is paper-only. This function controls only opening new paper positions.
    It does not affect managing existing positions.
    """

    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        now_local_dt = datetime.now(ZoneInfo("America/Los_Angeles"))
    except Exception:
        now_local_dt = datetime.now()

    now_local = now_local_dt.isoformat(timespec="seconds")
    hour = int(now_local_dt.hour)
    minute = int(now_local_dt.minute)
    minutes_now = hour * 60 + minute

    regular_open = 6 * 60 + 30
    regular_close = 13 * 60

    allow_premarket = bool(
        settings.get("allow_premarket_buys", False)
        or settings.get("premarket_buys_enabled", False)
        or settings.get("allow_extended_hours_buys", False)
    )

    # Premarket paper-buy window: 1:00 AM to 6:29 AM Pacific.
    # This lets V2 test premarket behavior, but still blocks overnight dead hours.
    premarket_open = int(settings.get("premarket_buy_start_minutes", 60))
    premarket_close = regular_open

    if allow_premarket and premarket_open <= minutes_now < premarket_close:
        return {
            "new_buys_allowed": True,
            "reason": "Premarket paper buys enabled.",
            "now_local": now_local,
            "session": "premarket",
        }

    if regular_open <= minutes_now <= regular_close:
        return {
            "new_buys_allowed": True,
            "reason": "Regular market paper buys enabled.",
            "now_local": now_local,
            "session": "regular",
        }

    if minutes_now < regular_open:
        return {
            "new_buys_allowed": False,
            "reason": "Before regular market open 06:30 Pacific: new paper buys disabled.",
            "now_local": now_local,
            "session": "before_open",
        }

    return {
        "new_buys_allowed": False,
        "reason": "After regular market close 13:00 Pacific: new paper buys disabled.",
        "now_local": now_local,
        "session": "after_close",
    }

def rotate_portfolio_for_better_candidates(
    account: Dict[str, Any],
    settings: Dict[str, Any],
    scored: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Portfolio rotation manager.

    Goal:
    - Keep total invested closer to target exposure.
    - If cash is low and strong candidates exist, trim weaker multi-share positions.
    - Do not fully close 20-day locked positions before minimum hold.
    """

    actions: List[Dict[str, Any]] = []

    if not settings.get("portfolio_rotation_enabled", True):
        return actions

    if not settings.get("allow_partial_trim_for_rotation", True):
        return actions

    account_metrics = calculate_account_metrics(account, settings)
    cash = safe_float(account_metrics.get("cash"), 0.0)
    invested = safe_float(account_metrics.get("total_invested_dollars"), 0.0)

    min_invested = safe_float(settings.get("min_invested_dollars"), 8000.0)
    target_cash = safe_float(settings.get("target_cash_reserve_dollars"), 1000.0)
    max_rotation_sells = int(settings.get("max_rotation_sells_per_scan", 2))

    if cash >= target_cash:
        return actions

    if invested < min_invested:
        return actions

    strong_candidates = [
        c for c in scored
        if c.get("decision") in {"BUY_CANDIDATE", "STRONG_BUY_CANDIDATE"}
    ]

    if not strong_candidates:
        return actions

    open_positions = account.setdefault("open_positions", {})

    position_rows = []
    for symbol, pos in open_positions.items():
        if not isinstance(pos, dict):
            continue

        shares = int(safe_float(pos.get("shares"), 0))
        if shares <= 1:
            continue

        position_rows.append({
            "symbol": str(symbol).upper(),
            "entry_score": safe_float(pos.get("entry_score"), 0.0),
            "last_price": safe_float(pos.get("last_price"), pos.get("entry_price")),
            "shares": shares,
            "pos": pos,
        })

    position_rows.sort(key=lambda row: row["entry_score"])

    for row in position_rows:
        if len(actions) >= max_rotation_sells:
            break

        symbol = row["symbol"]
        pos = row["pos"]
        current_shares = int(safe_float(pos.get("shares"), 0))

        if current_shares <= 1:
            continue

        trim_shares = 1
        price = safe_float(pos.get("last_price"), pos.get("entry_price"))

        if price <= 0:
            continue

        entry_price = safe_float(pos.get("entry_price"), price)
        value = round(trim_shares * price, 2)
        cost_basis = round(trim_shares * entry_price, 2)
        pnl = round(value - cost_basis, 2)
        pnl_pct = round(((price - entry_price) / entry_price) * 100.0, 2) if entry_price else 0.0

        pos["shares"] = current_shares - trim_shares
        pos["cost"] = round(safe_float(pos.get("shares"), 0) * entry_price, 2)

        account["cash"] = round(safe_float(account.get("cash"), 0.0) + value, 2)
        account["realized_pnl"] = round(safe_float(account.get("realized_pnl"), 0.0) + pnl, 2)

        trade = {
            "time": now_iso(),
            "action": "TRIM",
            "symbol": symbol,
            "engine_id": pos.get("engine_id"),
            "shares": trim_shares,
            "entry_price": entry_price,
            "exit_price": price,
            "value": value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "reason": "V2 portfolio rotation trim: freed cash while keeping at least 1 share for prediction test.",
            "engine": BUILD,
        }

        account.setdefault("closed_trades", []).append(trade)
        account.setdefault("trade_log", []).append(trade)
        actions.append(trade)

        cash += value

        if cash >= target_cash:
            break

    return actions
def run_one_scan() -> Dict[str, Any]:
    """
    Run one clean V2 scan.

    Flow:
    1. Load settings/account.
    2. Update existing open positions using Schwab quotes.
    3. Fetch fresh quotes for the watchlist.
    4. Run all enabled engines.
    5. Check market-hours buy window.
    6. Rotate/trim only if new buys are allowed.
    7. Buy candidates only if new buys are allowed.
    8. Save one complete status response.
    """

    settings = load_settings()
    account = load_account()

    buy_window = {
        "new_buys_allowed": False,
        "reason": "Buy window not checked yet.",
    }

    if not settings.get("v2_enabled", True):
        return save_status({
            "last_message": "V2 engine disabled in settings.",
            "last_action": "WAIT",
            "last_scan_time": now_iso(),
            "top_v2_candidates": [],
            "buy_actions": [],
            "sell_actions": [],
            "buy_window": buy_window,
        })

    sell_actions = manage_open_positions(account, settings)

    watchlist = list(settings.get("watchlist", []))
    if "contextual_options_shadow_v1" in settings.get("enabled_engines", []):
        watchlist = list(dict.fromkeys([*watchlist, *contextual_candidate_symbols(settings)]))
    if "nasdaq100_technical_clone_v1" in settings.get("enabled_engines", []):
        watchlist = list(dict.fromkeys([*watchlist, *nasdaq100_candidate_symbols(settings)]))
    quotes = get_real_v2_quotes(watchlist)

    try:
        evaluate_due_shadow_signals(quotes, settings)
        build_shadow_engine_scorecard(settings)
    except Exception:
        # Research accounting must never interrupt live monitoring or exits.
        pass

    scored = run_enabled_engines(quotes, settings)

    shadow_signal_result: Dict[str, Any] = {}
    try:
        shadow_signal_result = record_shadow_signals(scored, settings)
    except Exception as exc:
        shadow_signal_result = {"status": "error", "recorded": 0, "error": str(exc)}

    options_paper_result = {}
    try:
        option_rows = [
            row for row in scored
            if isinstance(row, dict) and str(row.get("engine_id")) == "options_research"
        ]
        options_paper_result = maybe_buy_from_research_rows(option_rows, settings)
    except Exception as exc:
        options_paper_result = {
            "status": "error",
            "message": f"Options paper manager error: {exc}",
            "actions": [],
        }

    buy_window = market_buy_window_status(settings)

    rotation_actions: List[Dict[str, Any]] = []
    if (
        settings.get("paper_trading_enabled", True)
        and buy_window.get("new_buys_allowed", False)
    ):
        rotation_actions = rotate_portfolio_for_better_candidates(account, settings, scored)

    buy_actions: List[Dict[str, Any]] = []
    friday_buys_this_scan = 0

    if settings.get("paper_trading_enabled", True) and buy_window.get("new_buys_allowed", False):
        daily_limit = max(0, int(settings.get("max_new_buys_per_day", 5)))
        already_bought_today = paper_buys_on_market_day(account, settings)
        remaining_today = max(0, daily_limit - already_bought_today)
        max_new = min(int(settings.get("max_new_buys_per_scan", 6)), remaining_today)

        manager_ranked = rank_candidates_for_manager(scored)

        for candidate in manager_ranked:
            if len(buy_actions) >= max_new:
                break

            if candidate.get("decision") not in {"BUY_CANDIDATE", "STRONG_BUY_CANDIDATE"}:
                continue

            engine_id_for_limit = str(candidate.get("engine_id") or "").strip()

            engine_rejection = engine_main_buying_rejection(candidate, settings)
            if engine_rejection:
                candidate["manager_decision"] = "REJECTED"
                candidate["manager_reason"] = engine_rejection
                continue

            cooldown_reason = symbol_stop_cooldown_reason(
                account,
                str(candidate.get("symbol") or ""),
                settings,
            )
            if cooldown_reason:
                candidate["manager_decision"] = "REJECTED"
                candidate["manager_reason"] = cooldown_reason
                continue

            if engine_id_for_limit == "prediction_friday":
                max_friday_buys = int(safe_float(settings.get("prediction_friday_max_buys_per_scan"), 1))
                max_friday_open = int(safe_float(settings.get("prediction_friday_max_open_positions"), 5))
                friday_reserve_cash = safe_float(settings.get("prediction_friday_min_cash_reserve"), 500.0)

                open_positions_for_limit = account.get("open_positions", {})
                if not isinstance(open_positions_for_limit, dict):
                    open_positions_for_limit = {}

                open_friday_count = 0
                for _sym, _pos in open_positions_for_limit.items():
                    if isinstance(_pos, dict) and str(_pos.get("engine_id") or "").strip() == "prediction_friday":
                        open_friday_count += 1

                current_cash_for_limit = safe_float(account.get("cash"), 0.0)

                if max_friday_buys >= 0 and friday_buys_this_scan >= max_friday_buys:
                    candidate["manager_decision"] = "REJECTED"
                    candidate["manager_reason"] = f"Friday buy limit reached: {friday_buys_this_scan}/{max_friday_buys} this scan."
                    continue

                if max_friday_open >= 0 and open_friday_count >= max_friday_open:
                    candidate["manager_decision"] = "REJECTED"
                    candidate["manager_reason"] = f"Friday open-position limit reached: {open_friday_count}/{max_friday_open}."
                    continue

                if current_cash_for_limit < friday_reserve_cash:
                    candidate["manager_decision"] = "REJECTED"
                    candidate["manager_reason"] = f"Friday cash reserve protected. Cash {current_cash_for_limit:.2f} below reserve {friday_reserve_cash:.2f}."
                    continue

            approval = approve_candidate_buy(
                account=account,
                settings=settings,
                candidate=candidate,
            )

            if not approval.get("approved"):
                candidate["manager_decision"] = "REJECTED"
                candidate["manager_reason"] = approval.get("reason")
                continue

            candidate["manager_decision"] = "APPROVED"
            candidate["manager_reason"] = approval.get("reason")
            candidate["approved_shares"] = approval.get("shares")
            candidate["approved_dollars"] = approval.get("approved_dollars")

            trade = buy_position(account, candidate, settings, approval=approval)

            if trade:
                buy_actions.append(trade)
                if str(candidate.get("engine_id") or "").strip() == "prediction_friday":
                    friday_buys_this_scan += 1

    save_account(account)

    all_sell_actions = sell_actions + rotation_actions

    if buy_actions:
        last_action = "BUY"
        message = f"V2 bought {len(buy_actions)} paper position(s)."
    elif all_sell_actions:
        last_action = "SELL"
        message = f"V2 sold/trimmed {len(all_sell_actions)} paper position(s)."
    else:
        last_action = "WAIT"
        if not buy_window.get("new_buys_allowed", False):
            message = "V2 scanned. New buys blocked: " + str(buy_window.get("reason", "outside buy window"))
        else:
            message = "V2 scanned. No new paper action."

    return save_status({
        "last_message": message,
        "last_action": last_action,
        "last_scan_time": now_iso(),
        "top_v2_candidates": scored[:80],
        "options_paper_manager": options_paper_result,
        "options_paper_account": options_paper_result.get("account") if isinstance(options_paper_result, dict) else {},
        "options_paper_actions": options_paper_result.get("actions", []) if isinstance(options_paper_result, dict) else [],
        "shadow_signal_journal": shadow_signal_result,
        "buy_actions": buy_actions,
        "sell_actions": all_sell_actions,
        "buy_window": buy_window,
    })

def engine_loop() -> None:
    settings = load_settings()
    interval = int(settings.get("scan_interval_seconds", 60))

    save_status({
        "last_message": "Clean V2 engine loop started.",
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




# --- V2 CLICK-TO-SELL SINGLE POSITION ---
def sell_one_symbol(symbol: str) -> Dict[str, Any]:
    """
    Sell one open V2 paper position immediately.

    Used by the owner V2 monitor when clicking an open position row.
    This is paper-only. It uses the latest Schwab quote when available.
    """
    symbol = str(symbol or "").upper().strip()

    if not symbol:
        return save_status({
            "last_message": "V2 single-position sell failed: blank symbol.",
            "last_action": "ERROR",
            "last_scan_time": now_iso(),
            "sell_actions": [],
        })

    account = load_account()
    open_positions = account.setdefault("open_positions", {})

    if symbol not in open_positions:
        return save_status({
            "last_message": f"V2 single-position sell skipped: {symbol} is not open.",
            "last_action": "WAIT",
            "last_scan_time": now_iso(),
            "sell_actions": [],
        })

    pos = open_positions.get(symbol) or {}

    shares = safe_float(pos.get("shares"), 0.0)
    entry_price = safe_float(pos.get("entry_price") or pos.get("entry") or pos.get("price"), 0.0)

    if shares <= 0:
        return save_status({
            "last_message": f"V2 single-position sell failed: {symbol} has invalid share count.",
            "last_action": "ERROR",
            "last_scan_time": now_iso(),
            "sell_actions": [],
        })

    price = safe_float(pos.get("last_price") or pos.get("last") or entry_price, entry_price)

    try:
        quotes = get_real_v2_quotes([symbol])
        if quotes:
            q = quotes[0]
            live_price = safe_float(
                q.get("price")
                or q.get("last")
                or q.get("lastPrice")
                or q.get("mark")
                or q.get("bid")
                or q.get("ask"),
                0.0,
            )
            if live_price > 0:
                price = live_price
    except Exception:
        pass

    value = shares * price
    cost = shares * entry_price
    pnl = value - cost
    pnl_pct = (pnl / cost * 100.0) if cost > 0 else 0.0

    action = {
        "time": now_iso(),
        "action": "SELL",
        "engine_id": pos.get("engine_id"),
        "symbol": symbol,
        "shares": shares,
        "entry_price": entry_price,
        "price": price,
        "value": value,
        "cost": cost,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "reason": "Manual owner click sell from V2 monitor.",
        "source": "owner_click_sell",
    }

    # Remove the open position.
    open_positions.pop(symbol, None)

    # Update cash.
    account["cash"] = safe_float(account.get("cash"), 0.0) + value

    # Save realized P/L totals if these fields exist or are used by monitor.
    account["realized_pnl"] = safe_float(account.get("realized_pnl"), 0.0) + pnl

    closed = account.setdefault("closed_trades", [])
    if isinstance(closed, list):
        closed.append(action)

    actions = account.setdefault("actions", [])
    if isinstance(actions, list):
        actions.append(action)

    try:
        save_account(account)
    except Exception:
        try:
            save_json(DATA_DIR / "v2_paper_account.json", account)
        except Exception:
            pass

    return save_status({
        "last_message": f"V2 owner click sold {symbol}.",
        "last_action": "SELL",
        "last_scan_time": now_iso(),
        "sell_actions": [action],
    })
# --- END V2 CLICK-TO-SELL SINGLE POSITION ---


def sell_all() -> Dict[str, Any]:
    account = load_account()
    open_positions = account.setdefault("open_positions", {})
    actions: List[Dict[str, Any]] = []

    for symbol, pos in list(open_positions.items()):
        price = safe_float(pos.get("last_price"), pos.get("entry_price"))
        trade = sell_position(account, symbol, price, "V2 manual sell all")
        if trade:
            actions.append(trade)

    save_account(account)

    return save_status({
        "last_message": f"V2 manual sell-all completed. Sold {len(actions)} position(s).",
        "last_action": "SELL_ALL",
        "last_scan_time": now_iso(),
        "sell_actions": actions,
    })









