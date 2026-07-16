from pathlib import Path

path = Path("alientai_v2/engine.py")
text = path.read_text(encoding="utf-8-sig")

patch = r'''

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
'''

if "def sell_one_symbol(" not in text:
    # Put this near the existing sell_all function if possible.
    marker = "def sell_all()"
    idx = text.find(marker)

    if idx != -1:
        text = text[:idx] + patch + "\n\n" + text[idx:]
    else:
        text = text.rstrip() + "\n\n" + patch + "\n"

path.write_text(text, encoding="utf-8")
