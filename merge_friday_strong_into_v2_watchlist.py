from pathlib import Path

watchlist_path = Path("v2_live_watchlist_symbols.txt")
friday_path = Path("prediction_friday_strong_symbols.txt")

watch = []
if watchlist_path.exists():
    watch = [x.strip().upper() for x in watchlist_path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]

friday = [x.strip().upper() for x in friday_path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]

merged = list(dict.fromkeys(watch + friday))

watchlist_path.write_text("\n".join(merged) + "\n", encoding="utf-8")

print("Original watchlist count:", len(watch))
print("Friday strong added:", len(friday))
print("New watchlist count:", len(merged))
print("Friday strong symbols:")
for s in friday:
    print(" ", s)
