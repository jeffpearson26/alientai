import csv
import json
from pathlib import Path
from collections import Counter

root = Path("data_v2/prediction_20day_daily_training")

summary_csv = root / "prediction_20day_daily_summary.csv"
policy_json = root / "prediction_20day_symbol_policy.json"
out_csv = root / "prediction_20day_daily_summary_with_policy.csv"

rows = []
with summary_csv.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    fieldnames = list(reader.fieldnames or [])

policy_data = json.loads(policy_json.read_text(encoding="utf-8-sig"))

symbol_policy = {}

for bucket_name, policy_name in [
    ("allow_buy", "ALLOW_BUY"),
    ("watch_only", "WATCH_ONLY"),
    ("block_buy", "BLOCK_BUY"),
]:
    for item in policy_data.get(bucket_name, []):
        if not isinstance(item, dict):
            continue

        symbol = str(item.get("symbol", "")).strip().upper()
        if symbol:
            symbol_policy[symbol] = str(item.get("policy") or policy_name)

if "policy" not in fieldnames:
    fieldnames.append("policy")

for row in rows:
    symbol = str(row.get("symbol", "")).strip().upper()
    row["policy"] = symbol_policy.get(symbol, "")

with out_csv.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("Wrote:", out_csv)
print("Rows:", len(rows))
print("Mapped symbols:", len(symbol_policy))
print("Policy counts:")
print(Counter(row.get("policy", "") for row in rows))
