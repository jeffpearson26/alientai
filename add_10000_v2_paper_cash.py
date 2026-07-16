import json
from pathlib import Path
from datetime import datetime

account_path = Path("data_v2/v2_paper_account.json")
backup_path = Path("data_v2/v2_paper_account_BACKUP_BEFORE_10000_PAPER_CASH_DEPOSIT.json")

deposit_amount = 10000.00

account = json.loads(account_path.read_text(encoding="utf-8"))

backup_path.write_text(json.dumps(account, indent=2), encoding="utf-8")

old_cash = float(account.get("cash") or 0)
old_starting_balance = float(account.get("starting_balance") or 0)

account["cash"] = round(old_cash + deposit_amount, 2)
account["starting_balance"] = round(old_starting_balance + deposit_amount, 2)
account["updated_at"] = datetime.now().isoformat(timespec="seconds")

actions = account.get("actions")
if not isinstance(actions, list):
    actions = []

actions.append({
    "time": datetime.now().isoformat(timespec="seconds"),
    "action": "PAPER_CASH_DEPOSIT",
    "amount": deposit_amount,
    "old_cash": old_cash,
    "new_cash": account["cash"],
    "old_starting_balance": old_starting_balance,
    "new_starting_balance": account["starting_balance"],
    "reason": "Owner added paper cash because existing cash was locked in minimum-hold positions.",
    "source": "owner_manual_paper_cash_deposit"
})

account["actions"] = actions

account_path.write_text(json.dumps(account, indent=2), encoding="utf-8")

print("Added paper cash deposit.")
print("backup =", backup_path)
print("old_cash =", old_cash)
print("new_cash =", account["cash"])
print("old_starting_balance =", old_starting_balance)
print("new_starting_balance =", account["starting_balance"])
