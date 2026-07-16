import json

from alientai_v2.engines.engine_registry import available_engines, run_enabled_engines

settings = json.load(open("data_v2/v2_settings.json", "r", encoding="utf-8-sig"))

quotes = [
    {
        "symbol": "AAOI",
        "price": 20.00,
        "move_pct": 1.5,
        "spread_pct": 0.05,
        "volume": 1000000,
        "source": "manual_registry_test",
    },
    {
        "symbol": "AMD",
        "price": 510.00,
        "move_pct": -1.5,
        "spread_pct": 0.05,
        "volume": 10000000,
        "source": "manual_registry_test",
    },
]

print("available_engines:", available_engines())
print("enabled_engines:", settings.get("enabled_engines"))

rows = run_enabled_engines(quotes, settings)

print("rows:", len(rows))

for row in rows:
    print(row.get("engine_id"), row.get("symbol"), row.get("decision"), row.get("score"), row.get("reason"))

