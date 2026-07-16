import json
from pathlib import Path

p = Path("data_v2/similarity_percentile_sandbox/similarity_percentile_sandbox_account.json")

if not p.exists():
    raise SystemExit("Missing percentile sandbox account.")

a = json.loads(p.read_text(encoding="utf-8"))

print("SIMILARITY PERCENTILE SANDBOX ACCOUNT")
print("-" * 100)
print("Engine:", a.get("engine_id"))
print("Mode:", a.get("mode"))
print("Real trading enabled:", a.get("real_trading_enabled"))
print("Main V2 buying enabled:", a.get("main_v2_buying_enabled"))
print("Threshold mode:", a.get("threshold_mode"))
print("")
print("Starting balance: ${:,.2f}".format(float(a.get("starting_balance", 0))))
print("Cash:             ${:,.2f}".format(float(a.get("cash", 0))))
print("Open value:       ${:,.2f}".format(float(a.get("open_position_value", 0))))
print("Account value:    ${:,.2f}".format(float(a.get("account_value", 0))))
print("Realized P/L:     ${:,.2f}".format(float(a.get("realized_pnl", 0))))
print("Unrealized P/L:   ${:,.2f}".format(float(a.get("unrealized_pnl", 0))))
print("Total P/L:        ${:,.2f}".format(float(a.get("total_pnl", 0))))
print("Total P/L %:      {:.4f}%".format(float(a.get("total_pnl_pct", 0))))
print("")
print("Open positions:", len(a.get("open_positions", {})))
print("-" * 100)

for sym, pos in a.get("open_positions", {}).items():
    print(
        sym,
        "| shares:", pos.get("shares"),
        "| entry:", pos.get("entry_price"),
        "| last:", pos.get("last_price"),
        "| value:", pos.get("market_value"),
        "| P/L:", pos.get("unrealized_pnl"),
        "| P/L %:", pos.get("unrealized_pnl_pct"),
        "| score:", pos.get("similarity_score"),
        "| locked until:", pos.get("min_hold_until"),
    )

last_scan = a.get("last_scan", {})
print("")
print("LAST SCAN")
print("-" * 100)
print("Time:", last_scan.get("time"))
print("Build:", last_scan.get("build"))
print("Buys:", len(last_scan.get("buys", [])))

print("")
print("Last buys:")
for b in last_scan.get("buys", []):
    print(
        b.get("symbol"),
        "| shares:", b.get("shares"),
        "| price:", b.get("price"),
        "| cost:", b.get("cost"),
        "| score:", b.get("score"),
    )
