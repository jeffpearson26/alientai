import json
from pathlib import Path

path = Path("data_v2/v2_settings.json")
settings = json.loads(path.read_text(encoding="utf-8-sig"))

enabled = settings.get("enabled_engines", [])
if not isinstance(enabled, list):
    enabled = []

for engine in [
    "prediction_20day",
    "momentum_5min",
    "similarity_engine",
    "transformer_20day",
    "options_research",
]:
    if engine not in enabled:
        enabled.append(engine)

settings["enabled_engines"] = enabled

settings["options_research_enabled"] = True
settings["options_paper_trading_enabled"] = False
settings["options_live_trading_enabled"] = False

settings["options_research_symbols"] = ["MARA", "RIVN", "PLTR", "SOXL"]
settings["options_research_contract_type"] = "CALL"
settings["options_research_min_dte"] = 14
settings["options_research_max_dte"] = 45
settings["options_research_max_spread_pct"] = 20.0
settings["options_research_max_contract_price"] = 8.0
settings["options_research_max_contracts_per_symbol"] = 3
settings["options_research_max_symbols_per_scan"] = 4
settings["options_research_strike_count"] = 20

path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

print("enabled_engines:", settings["enabled_engines"])
print("options_research_symbols:", settings["options_research_symbols"])
