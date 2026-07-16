import json
from pathlib import Path
from datetime import datetime

settings_path = Path("data_v2/v2_settings.json")
backup_path = Path("data_v2/v2_settings_BACKUP_BEFORE_OPTIONS_RESEARCH_MORE_BUYS.json")

if not settings_path.exists():
    raise SystemExit("Missing data_v2/v2_settings.json")

settings = json.loads(settings_path.read_text(encoding="utf-8"))
backup_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

updates = {
    # Main paper options switches
    "options_paper_trading_enabled": True,
    "options_paper_buy_enabled": True,
    "options_research_enabled": True,
    "options_research_paper_buy_enabled": True,

    # Candidate quality gate
    "options_min_score_to_buy": 90.0,
    "min_options_score_to_buy": 90.0,
    "options_min_candidate_score": 90.0,
    "options_research_min_score_to_buy": 90.0,

    # Buying limits
    "options_max_new_buys_per_scan": 2,
    "max_new_option_buys_per_scan": 2,
    "options_research_max_new_buys_per_scan": 2,

    # Position limits
    "options_max_open_positions": 6,
    "max_open_option_positions": 6,
    "options_research_max_open_positions": 6,

    # Contract / cost limits
    "options_max_contracts_per_trade": 1,
    "max_option_contracts_per_trade": 1,
    "options_research_max_contracts_per_trade": 1,

    "options_max_trade_cost": 250.0,
    "max_option_trade_cost": 250.0,
    "options_research_max_trade_cost": 250.0,

    # Account exposure guard
    "options_max_total_exposure": 1500.0,
    "max_options_total_exposure": 1500.0,
    "options_research_max_total_exposure": 1500.0,

    # Spread guard for options. Options spreads are wider than stocks,
    # so this is looser than stock rules but still blocks terrible fills.
    "options_max_spread_pct": 25.0,
    "options_research_max_spread_pct": 25.0,

    # Safety note
    "options_real_trading_enabled": False,
    "live_options_trading_enabled": False,
}

old_values = {}

for key, value in updates.items():
    old_values[key] = settings.get(key)
    settings[key] = value

settings["updated_at"] = datetime.now().isoformat(timespec="seconds")
settings["options_research_note"] = (
    "Options research paper buys enabled with score >= 90, small size, "
    "1 contract max per trade, and strict sandbox exposure limits. "
    "Real options trading remains disabled."
)

settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

print("Enabled paper-only options research buys.")
print("Backup:", backup_path)
print("")
print("Changed settings:")
for key in updates:
    print(f"{key}:", old_values[key], "->", settings[key])
