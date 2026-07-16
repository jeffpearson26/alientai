from pathlib import Path

watchlist_path = Path("v2_live_watchlist_symbols.txt")
sp500_friday_path = Path("prediction_friday_sp500_strong_symbols.txt")

watch = []
if watchlist_path.exists():
    watch = [
        x.strip().upper()
        for x in watchlist_path.read_text(encoding="utf-8-sig").splitlines()
        if x.strip()
    ]

sp500 = [
    x.strip().upper()
    for x in sp500_friday_path.read_text(encoding="utf-8-sig").splitlines()
    if x.strip()
]

merged = list(dict.fromkeys(watch + sp500))

watchlist_path.write_text("\n".join(merged) + "\n", encoding="utf-8")

print("Original watchlist count:", len(watch))
print("S&P Friday strong added:", len([s for s in sp500 if s not in watch]))
print("New watchlist count:", len(merged))
print("")
print("S&P Friday strong symbols:")
for s in sp500:
    print(" ", s)
