import json
from pathlib import Path

path = Path("data_v2/v2_settings.json")
settings = json.loads(path.read_text(encoding="utf-8-sig"))

settings["options_research_enabled"] = True
settings["options_paper_trading_enabled"] = False
settings["options_live_trading_enabled"] = False

settings["options_research_contract_type"] = "CALL"
settings["options_research_min_dte"] = 14
settings["options_research_max_dte"] = 45
settings["options_research_max_spread_pct"] = 15.0
settings["options_research_min_open_interest"] = 1
settings["options_research_min_volume"] = 0
settings["options_research_max_contract_price"] = 8.00
settings["options_research_max_contracts_per_symbol"] = 3
settings["options_research_underlying_sources"] = [
    "prediction_20day",
    "momentum_5min",
    "transformer_20day"
]

path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

print("Options research settings added.")
for key in [
    "options_research_enabled",
    "options_paper_trading_enabled",
    "options_live_trading_enabled",
    "options_research_contract_type",
    "options_research_min_dte",
    "options_research_max_dte",
    "options_research_max_spread_pct",
    "options_research_max_contract_price",
]:
    print(key, "=", settings.get(key))
