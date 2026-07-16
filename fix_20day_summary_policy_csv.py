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

def get_policy_for_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    item = policy_data.get(symbol)

    if isinstance(item, dict):
        return str(
            item.get("policy")
            or item.get("daily_policy")
            or item.get("prediction_20day_policy")
            or ""
        )

    if item is None:
        return ""

    return str(item)

if "policy" not in fieldnames:
    fieldnames.append("policy")

for row in rows:
    symbol = str(row.get("symbol", "")).strip().upper()
    row["policy"] = get_policy_for_symbol(symbol)

with out_csv.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("Wrote:", out_csv)
print("Rows:", len(rows))
print("Policy counts:")
print(Counter(row.get("policy", "") for row in rows))
