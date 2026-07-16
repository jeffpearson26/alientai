import json
from pathlib import Path

settings_path = Path("data_v2/v2_settings.json")

settings = json.loads(settings_path.read_text(encoding="utf-8-sig"))

# Allow V2 paper buys before regular market open.
settings["allow_premarket_buys"] = True
settings["premarket_buys_enabled"] = True
settings["allow_extended_hours_buys"] = True

# Keep V2 paper-only and keep old scanner brain off.
settings["v2_enabled"] = True
settings["paper_trading_enabled"] = True
settings["old_scanner_decision_making_enabled"] = False

# Master policy is now hard-wired in prediction_20day.py, but keep this setting for clarity.
settings["prediction_20day_use_master_policy"] = True

settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

print("Updated settings:")
for key in [
    "allow_premarket_buys",
    "premarket_buys_enabled",
    "allow_extended_hours_buys",
    "v2_enabled",
    "paper_trading_enabled",
    "old_scanner_decision_making_enabled",
    "prediction_20day_use_master_policy",
]:
    print(key, "=", settings.get(key))
