import json
from pathlib import Path

settings_path = Path("data_v2/v2_settings.json")
watchlist_path = Path("v2_live_watchlist_symbols.txt")

settings = json.loads(settings_path.read_text(encoding="utf-8-sig"))

file_watchlist = [
    x.strip().upper()
    for x in watchlist_path.read_text(encoding="utf-8-sig").splitlines()
    if x.strip()
]

# Put the same watchlist into every likely V2 setting key.
settings["watchlist"] = file_watchlist
settings["symbols"] = file_watchlist
settings["v2_watchlist"] = file_watchlist
settings["v2_live_watchlist"] = file_watchlist
settings["live_watchlist"] = file_watchlist

settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

print("Wrote watchlist into v2_settings.json")
print("Watchlist count:", len(file_watchlist))
print("Last 20 symbols:")
for s in file_watchlist[-20:]:
    print(" ", s)
