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
settings["prediction_friday_enabled"] = True
settings["prediction_friday_horizon_days"] = 5.0
settings["prediction_friday_minimum_hold_minutes"] = 7200.0

# Keep it conservative at first.
settings["prediction_friday_buying_enabled"] = False
settings["prediction_friday_confirmation_only"] = True

path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

print("enabled_engines =", settings["enabled_engines"])
print("prediction_friday_enabled =", settings["prediction_friday_enabled"])
print("prediction_friday_confirmation_only =", settings["prediction_friday_confirmation_only"])
