from __future__ import annotations

"""Make the frozen Nasdaq-101 baseline the sole enabled V2 paper model."""

import json
import os
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = PROJECT_ROOT / "data_v2" / "v2_settings.json"
WATCHLIST_PATH = PROJECT_ROOT / "v2_live_watchlist_symbols.txt"
SYMBOLS_PATH = PROJECT_ROOT / "nasdaq100_2026-06_symbols.txt"
MODEL_ID = "nasdaq100_complete_101_baseline_v1"


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> None:
    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    symbols = [
        line.strip().upper()
        for line in SYMBOLS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(symbols) != 101 or len(set(symbols)) != 101:
        raise ValueError("Nasdaq-101 paper configuration requires exactly 101 unique symbols")

    settings.update({
        "v2_enabled": True,
        "paper_trading_enabled": True,
        "enabled_engines": [MODEL_ID],
        "main_account_enabled_buy_engines": [MODEL_ID],
        "nasdaq101_baseline_paper_enabled": True,
        "nasdaq101_baseline_payload_max_calendar_age_days": 3,
        "nasdaq101_baseline_max_candidates": 5,
        "nasdaq101_baseline_stop_loss_pct": -1.0,
        "nasdaq101_baseline_trailing_stop_pct": 5.0,
        "nasdaq101_baseline_pyramid_enabled": True,
        "nasdaq101_baseline_pyramid_interval_seconds": 300,
        "nasdaq101_baseline_pyramid_shares": 1,
        "nasdaq100_technical_clone_paper_enabled": False,
        "contextual_options_paper_enabled": False,
        "prediction_friday_enabled": False,
        "prediction_friday_buying_enabled": False,
        "similarity_engine_sandbox_enabled": False,
        "similarity_engine_main_v2_buying_enabled": False,
        "options_paper_trading_enabled": False,
        "options_live_trading_enabled": False,
        "options_real_trading_enabled": False,
        "live_options_trading_enabled": False,
        "similarity_engine_sandbox_real_trading_enabled": False,
        "old_scanner_decision_making_enabled": False,
        "watchlist": symbols,
        "symbols": symbols,
        "v2_watchlist": symbols,
        "v2_live_watchlist": symbols,
        "live_watchlist": symbols,
        "watchlist_source": "v2_live_watchlist_symbols.txt",
        "watchlist_count": len(symbols),
    })
    _atomic_text(SETTINGS_PATH, json.dumps(settings, indent=2) + "\n")
    _atomic_text(WATCHLIST_PATH, "\n".join(symbols) + "\n")
    print(json.dumps({
        "status": "configured",
        "paper_trading_enabled": settings["paper_trading_enabled"],
        "enabled_engines": settings["enabled_engines"],
        "main_account_enabled_buy_engines": settings["main_account_enabled_buy_engines"],
        "watchlist_count": len(symbols),
        "all_live_trading_flags": False,
    }, indent=2))


if __name__ == "__main__":
    main()
