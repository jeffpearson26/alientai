import json
from pathlib import Path

account_path = Path("data_v2/similarity_engine_sandbox/similarity_engine_sandbox_account.json")

if not account_path.exists():
    raise SystemExit("Missing sandbox account. Run init_similarity_engine_sandbox_account.py first.")

a = json.loads(account_path.read_text(encoding="utf-8"))

print("SIMILARITY ENGINE SANDBOX ACCOUNT")
print("-" * 90)
print("Engine:", a.get("engine_id"))
print("Mode:", a.get("mode"))
print("Real trading enabled:", a.get("real_trading_enabled"))
print("Main V2 buying enabled:", a.get("main_v2_buying_enabled"))
print("")
print("Starting balance: ${:,.2f}".format(float(a.get("starting_balance", 0))))
print("Cash:             ${:,.2f}".format(float(a.get("cash", 0))))
print("Open value:       ${:,.2f}".format(float(a.get("open_position_value", 0))))
print("Account value:    ${:,.2f}".format(float(a.get("account_value", 0))))
print("Realized P/L:     ${:,.2f}".format(float(a.get("realized_pnl", 0))))
print("Unrealized P/L:   ${:,.2f}".format(float(a.get("unrealized_pnl", 0))))
print("Total P/L:        ${:,.2f}".format(float(a.get("total_pnl", 0))))
print("")
print("Max position dollars:", a.get("max_position_dollars"))
print("Max open positions:", a.get("max_open_positions"))
print("Minimum hold days:", a.get("min_hold_days"))
print("")
print("Allowed symbols:")
for sym in a.get("allowed_symbols", []):
    print(" ", sym)

print("")
print("Open positions:", len(a.get("open_positions", {})))
for sym, pos in a.get("open_positions", {}).items():
    print(sym, pos)
