import json
from pathlib import Path

settings_path = Path("data_v2/v2_settings.json")
settings = json.loads(settings_path.read_text(encoding="utf-8-sig"))

settings["options_research_enabled"] = True
settings["options_paper_trading_enabled"] = True
settings["options_live_trading_enabled"] = False

# Separate paper-options bankroll.
settings["options_paper_starting_balance"] = 1000.0

# Let it use profits naturally by spending from the options paper account cash.
settings["options_paper_use_profits"] = True

# Conservative first settings.
settings["options_paper_max_position_cost"] = 250.0
settings["options_paper_max_open_positions"] = 5
settings["options_paper_max_positions_per_underlying"] = 1
settings["options_paper_max_buys_per_scan"] = 1

# Keep research filter at affordable options only for paper buying.
settings["options_research_max_contract_price"] = 8.0
settings["options_research_max_spread_pct"] = 20.0
settings["options_research_symbols"] = ["MARA", "RIVN", "PLTR", "SOXL"]

settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

print("Options paper trading enabled.")
print("options_paper_trading_enabled =", settings["options_paper_trading_enabled"])
print("options_live_trading_enabled =", settings["options_live_trading_enabled"])
print("options_paper_starting_balance =", settings["options_paper_starting_balance"])
print("options_paper_max_position_cost =", settings["options_paper_max_position_cost"])
print("options_paper_max_buys_per_scan =", settings["options_paper_max_buys_per_scan"])
