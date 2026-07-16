from pathlib import Path

path = Path("alientai_v2/engine.py")
text = path.read_text(encoding="utf-8-sig")

needle = '''def market_buy_window_status(settings: Dict[str, Any]) -> Dict[str, Any]:
'''

if needle not in text:
    raise SystemExit("Could not find market_buy_window_status function.")

start = text.index(needle)

# Find next function after market_buy_window_status.
next_def = text.find("\ndef ", start + len(needle))
if next_def == -1:
    raise SystemExit("Could not find end of market_buy_window_status function.")

old_func = text[start:next_def]

new_func = r'''def market_buy_window_status(settings: Dict[str, Any]) -> Dict[str, Any]:
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
'''

text = text[:start] + new_func + text[next_def:]

path.write_text(text, encoding="utf-8")
