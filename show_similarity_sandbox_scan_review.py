import json
from pathlib import Path

account_path = Path("data_v2/similarity_engine_sandbox/similarity_engine_sandbox_account.json")

if not account_path.exists():
    raise SystemExit("Missing similarity sandbox account.")

a = json.loads(account_path.read_text(encoding="utf-8"))

last_scan = a.get("last_scan", {})
candidates = last_scan.get("candidates", [])
threshold = float(last_scan.get("score_threshold") or a.get("score_threshold") or 51.5)

print("SIMILARITY SANDBOX SCAN REVIEW")
print("-" * 100)
print("Last scan:", last_scan.get("time"))
print("Buy threshold:", threshold)
print("Cash: ${:,.2f}".format(float(a.get("cash", 0))))
print("Open value: ${:,.2f}".format(float(a.get("open_position_value", 0))))
print("Account value: ${:,.2f}".format(float(a.get("account_value", 0))))
print("Open positions:", len(a.get("open_positions", {})))
print("")

ranked = []
for c in candidates:
    score = c.get("score")
    if score == "" or score is None:
        continue
    try:
        score = float(score)
    except Exception:
        continue

    ranked.append({
        "symbol": c.get("symbol"),
        "status": c.get("status"),
        "score": score,
        "below_buy": threshold - score,
        "last_price": c.get("last_price"),
        "result": c.get("buy_result", ""),
        "reason": c.get("reason", ""),
    })

ranked.sort(key=lambda x: x["score"], reverse=True)

print("RANKED CURRENT SIGNALS")
print("-" * 100)
print(f"{'SYMBOL':8} {'STATUS':12} {'SCORE':>10} {'BELOW BUY':>12} {'LAST':>12} {'RESULT':18}")
print("-" * 100)

for r in ranked:
    print(
        f"{str(r['symbol']):8} "
        f"{str(r['status']):12} "
        f"{r['score']:10.4f} "
        f"{r['below_buy']:12.4f} "
        f"{str(r['last_price']):>12} "
        f"{str(r['result']):18}"
    )

print("")
if ranked and ranked[0]["score"] < threshold:
    best = ranked[0]
    print(f"Closest to buy: {best['symbol']} at {best['score']:.4f}, which is {best['below_buy']:.4f} below threshold.")
elif ranked:
    print("At least one symbol met the buy threshold.")
else:
    print("No scored candidates found.")
