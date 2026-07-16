import json
from pathlib import Path

summary_path = Path("data_v2/engine_accounts/engine_accounts_summary.json")

summary = json.loads(summary_path.read_text(encoding="utf-8"))

print("ENGINE SCOREBOARD")
print("-" * 115)
print("{:<40} {:>12} {:>12} {:>10} {:>6} {:>7} {:>8}".format(
    "ENGINE", "VALUE", "P/L", "P/L %", "OPEN", "CLOSED", "WIN %"
))
print("-" * 115)

for e in summary.get("engines", []):
    engine_id = str(e.get("engine_id", ""))[:40]
    account_value = float(e.get("account_value") or 0)
    total_pnl = float(e.get("total_pnl") or 0)
    total_pnl_pct = float(e.get("total_pnl_pct") or 0)
    open_positions = int(e.get("open_positions_count") or 0)
    closed_trades = int(e.get("closed_trades_count") or 0)
    win_rate = float(e.get("closed_win_rate_pct") or 0)

    print("{:<40} {:>12.2f} {:>12.2f} {:>10.3f} {:>6} {:>7} {:>8.2f}".format(
        engine_id,
        account_value,
        total_pnl,
        total_pnl_pct,
        open_positions,
        closed_trades,
        win_rate,
    ))
