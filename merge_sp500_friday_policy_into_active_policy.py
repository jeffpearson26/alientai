import json
from pathlib import Path
from datetime import datetime

main_path = Path("data_v2/prediction_friday_daily_training/prediction_friday_symbol_policy.json")
sp500_path = Path("data_v2/prediction_friday_sp500_daily_training/prediction_friday_sp500_symbol_policy.json")

if not main_path.exists():
    raise SystemExit(f"Missing main Friday policy: {main_path}")

if not sp500_path.exists():
    raise SystemExit(f"Missing S&P Friday policy: {sp500_path}")

main_policy = json.loads(main_path.read_text(encoding="utf-8-sig"))
sp500_policy = json.loads(sp500_path.read_text(encoding="utf-8-sig"))

backup_path = main_path.with_name(
    "prediction_friday_symbol_policy_BACKUP_BEFORE_SP500_MERGE_" +
    datetime.now().strftime("%Y%m%d_%H%M%S") +
    ".json"
)
backup_path.write_text(json.dumps(main_policy, indent=2), encoding="utf-8")

def score_policy(row):
    policy_rank = {
        "ALLOW_BUY_STRONG": 4,
        "ALLOW_BUY": 3,
        "WATCH_ONLY": 2,
        "BLOCK_BUY": 1,
        "NO_DATA": 0,
    }

    policy = str(row.get("policy") or "NO_DATA").upper()
    win = float(row.get("buy_candidate_win_rate_pct") or 0)
    avg = float(row.get("avg_buy_future_friday_return_pct") or 0)
    buys = float(row.get("buy_candidates") or 0)

    return (
        policy_rank.get(policy, 0),
        win,
        avg,
        buys,
    )

merged = dict(main_policy)

added = 0
replaced = 0
kept_existing = 0

for symbol, sp_row in sp500_policy.items():
    symbol = str(symbol).upper().strip()
    if not isinstance(sp_row, dict):
        continue

    sp_row = dict(sp_row)
    sp_row["friday_policy_universe"] = "SP500"

    if symbol not in merged:
        merged[symbol] = sp_row
        added += 1
        continue

    existing = merged[symbol]
    if not isinstance(existing, dict):
        merged[symbol] = sp_row
        replaced += 1
        continue

    existing_score = score_policy(existing)
    sp_score = score_policy(sp_row)

    # Keep whichever policy is stronger for that symbol.
    if sp_score > existing_score:
        existing["friday_policy_replaced_by_sp500_backup"] = True
        sp_row["friday_policy_replaced_existing_policy"] = True
        merged[symbol] = sp_row
        replaced += 1
    else:
        existing["friday_policy_universe"] = existing.get("friday_policy_universe", "RUSSELL_SUPABASE")
        kept_existing += 1

main_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")

print("Merged S&P Friday policy into active Friday policy.")
print("Main policy symbols before:", len(main_policy))
print("S&P policy symbols:", len(sp500_policy))
print("Merged policy symbols:", len(merged))
print("Added:", added)
print("Replaced with stronger S&P policy:", replaced)
print("Kept existing stronger policy:", kept_existing)
print("Backup:", backup_path)
