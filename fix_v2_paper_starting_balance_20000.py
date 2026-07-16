import json
from pathlib import Path
from datetime import datetime

account_path = Path("data_v2/v2_paper_account.json")
backup_path = Path("data_v2/v2_paper_account_BACKUP_BEFORE_STARTING_BALANCE_20000_FIX.json")

account = json.loads(account_path.read_text(encoding="utf-8"))
backup_path.write_text(json.dumps(account, indent=2), encoding="utf-8")

old_starting_balance = float(account.get("starting_balance") or 0)

account["starting_balance"] = 20000.0
account["updated_at"] = datetime.now().isoformat(timespec="seconds")

actions = account.get("actions")
if not isinstance(actions, list):
    actions = []

actions.append({
    "time": datetime.now().isoformat(timespec="seconds"),
    "action": "PAPER_STARTING_BALANCE_FIX",
    "old_starting_balance": old_starting_balance,
    "new_starting_balance": 20000.0,
    "reason": "Corrected paper starting balance after adding another $10,000 paper cash.",
    "source": "owner_manual_paper_accounting_fix"
})

account["actions"] = actions

account_path.write_text(json.dumps(account, indent=2), encoding="utf-8")

print("Fixed starting_balance.")
print("backup =", backup_path)
print("old_starting_balance =", old_starting_balance)
print("new_starting_balance =", account["starting_balance"])
print("cash =", account.get("cash"))
print("open_positions =", len(account.get("open_positions", {})))
