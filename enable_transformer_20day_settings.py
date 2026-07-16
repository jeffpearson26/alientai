import json
from pathlib import Path

path = Path("data_v2/v2_settings.json")
settings = json.loads(path.read_text(encoding="utf-8-sig"))

enabled = settings.get("enabled_engines", [])

if not isinstance(enabled, list):
    enabled = []

for engine in ["prediction_20day", "momentum_5min", "similarity_engine", "transformer_20day"]:
    if engine not in enabled:
        enabled.append(engine)

settings["enabled_engines"] = enabled

# Conservative transformer settings.
settings["transformer_20day_min_watch_probability"] = 0.60
settings["transformer_20day_min_buy_probability"] = 0.70
settings["transformer_20day_max_symbols_per_scan"] = 40
settings["transformer_20day_candle_limit"] = 280
settings["transformer_20day_symbol_delay_seconds"] = 0.02
settings["transformer_20day_daily_table"] = "v2_daily_candles"

path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

print("enabled_engines:", settings["enabled_engines"])
print("transformer min watch:", settings["transformer_20day_min_watch_probability"])
print("transformer min buy:", settings["transformer_20day_min_buy_probability"])
