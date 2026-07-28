from __future__ import annotations

import json
from pathlib import Path

from typing import Any, Dict

from alientai_v2.utils import DATA_DIR, load_json, save_json


SETTINGS_FILE = DATA_DIR / "v2_settings.json"


DEFAULT_SETTINGS: Dict[str, Any] = {
    "v2_enabled": True,
    "paper_trading_enabled": True,
    "old_scanner_decision_making_enabled": False,

    # Fail closed: research engines cannot buy the shared main account until
    # they pass validation and are explicitly added here.
    "main_account_enabled_buy_engines": [],
    "shadow_signal_journal_enabled": True,
    "shadow_signal_decisions": ["BUY_CANDIDATE", "STRONG_BUY_CANDIDATE"],
    "shadow_signal_round_trip_cost_pct": 0.25,
    "shadow_scorecard_min_completed_signals": 100,
    "shadow_scorecard_min_profit_factor": 1.20,

    # Transformer challenger signals are journaled for forward research only.
    # This threshold never changes the engine's execution BUY threshold.
    "transformer_20day_shadow_research_enabled": True,
    "transformer_20day_shadow_min_probability": 0.55,

    "starting_cash": 10000.0,

    "small_position_dollars": 500.0,
    "max_position_dollars": 500.0,
    "max_single_share_price": 2500.0,
    "max_open_positions": 25,
    "max_new_buys_per_scan": 6,
    "max_new_buys_per_day": 5,
    "max_shares_per_paper_trade": 0,
    "contextual_options_payload_max_calendar_age_days": 3,
    "nasdaq100_payload_max_calendar_age_days": 3,

    "prediction_horizon_days": 20.0,
    "minimum_hold_minutes": 28800.0,
    "max_hold_minutes": 28800.0,

    "respect_prediction_horizon": True,
    "hold_overnight": True,
    "sell_all_by_close_enabled": False,
    "sell_before_close_enabled": False,
    "sell_all_before_close_enabled": False,
    "before_close_liquidation_enabled": False,

    "take_profit_pct": 3.0,
    "stop_loss_pct": -1.5,
    "trailing_stop_pct": 1.0,
    "trailing_stop_activation_pct": 1.0,

    # A strategy horizon may delay ordinary exits, but never this hard-loss exit.
    "emergency_stop_enabled": True,
    "emergency_stop_loss_pct": -5.0,

    # Prevent an engine from immediately recreating a position just stopped out.
    "stop_reentry_cooldown_enabled": True,
    "stop_reentry_cooldown_hours": 168.0,

    "allow_stop_before_min_hold": False,
    "allow_trailing_before_min_hold": False,
    "allow_take_profit_before_min_hold": False,

    "scan_interval_seconds": 60,

    "watchlist": [
        "NVDA", "AMD", "AVGO", "TSM", "ASML", "ARM", "MU",
        "AMAT", "LRCX", "KLAC", "MRVL", "SMCI",
        "PLTR", "RIVN", "TSLA", "AAPL", "MSFT",
        "QQQ", "SPY", "IWM",
    ],
}


def load_settings() -> Dict[str, Any]:
    settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())

    if not isinstance(settings, dict):
        settings = DEFAULT_SETTINGS.copy()

    changed = False

    for key, value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = value
            changed = True

    # Force V2 safety intent.
    settings["old_scanner_decision_making_enabled"] = False
    settings["hold_overnight"] = True
    settings["respect_prediction_horizon"] = True
    settings["sell_all_by_close_enabled"] = False
    settings["sell_before_close_enabled"] = False
    settings["sell_all_before_close_enabled"] = False
    settings["before_close_liquidation_enabled"] = False

    if changed or not SETTINGS_FILE.exists():
        save_json(SETTINGS_FILE, settings)

    return apply_live_watchlist_priority(settings)


def save_settings(settings: Dict[str, Any]) -> None:
    save_json(SETTINGS_FILE, settings)


def load_watchlist_file_symbols() -> list[str]:
    """
    Highest-priority live V2 watchlist loader.

    This intentionally reads v2_live_watchlist_symbols.txt directly so V2 does not
    get stuck on DEFAULT_SETTINGS or an older settings object.
    """
    project_root = Path(__file__).resolve().parents[1]
    watchlist_path = project_root / "v2_live_watchlist_symbols.txt"

    if not watchlist_path.exists():
        return []

    try:
        symbols = [
            x.strip().upper()
            for x in watchlist_path.read_text(encoding="utf-8-sig").splitlines()
            if x.strip() and not x.strip().startswith("#")
        ]
        return list(dict.fromkeys(symbols))
    except Exception:
        return []


def apply_live_watchlist_priority(settings: dict) -> dict:
    """
    Force the live file watchlist to override default/settings watchlists.
    """
    if not isinstance(settings, dict):
        settings = {}

    file_symbols = load_watchlist_file_symbols()

    if file_symbols:
        settings["watchlist"] = file_symbols
        settings["symbols"] = file_symbols
        settings["v2_watchlist"] = file_symbols
        settings["v2_live_watchlist"] = file_symbols
        settings["live_watchlist"] = file_symbols
        settings["watchlist_source"] = "v2_live_watchlist_symbols.txt"
        settings["watchlist_count"] = len(file_symbols)

    return settings

