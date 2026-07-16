import json
from pathlib import Path

path = Path("data_v2/v2_settings.json")
settings = json.loads(path.read_text(encoding="utf-8-sig"))

enabled = settings.get("enabled_engines", [])
if not isinstance(enabled, list):
    enabled = []

if "prediction_friday" not in enabled:
    if "prediction_20day" in enabled:
        enabled.insert(enabled.index("prediction_20day") + 1, "prediction_friday")
    else:
        enabled.append("prediction_friday")

settings["enabled_engines"] = enabled

# Paper only.
settings["paper_trading_enabled"] = True
settings["options_live_trading_enabled"] = False

# Friday engine buying enabled, but strong-only.
settings["prediction_friday_enabled"] = True
settings["prediction_friday_buying_enabled"] = True
settings["prediction_friday_confirmation_only"] = False
settings["prediction_friday_buy_policies"] = ["ALLOW_BUY_STRONG"]

# Safety.
settings["prediction_friday_horizon_days"] = 5.0
settings["prediction_friday_minimum_hold_minutes"] = 7200.0
settings["prediction_friday_max_buys_per_scan"] = 1
settings["prediction_friday_max_position_dollars"] = 500.0

path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

print("enabled_engines =", settings["enabled_engines"])
print("prediction_friday_buying_enabled =", settings["prediction_friday_buying_enabled"])
print("prediction_friday_confirmation_only =", settings["prediction_friday_confirmation_only"])
print("prediction_friday_buy_policies =", settings["prediction_friday_buy_policies"])
print("prediction_friday_max_buys_per_scan =", settings["prediction_friday_max_buys_per_scan"])
print("prediction_friday_max_position_dollars =", settings["prediction_friday_max_position_dollars"])
