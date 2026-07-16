from pathlib import Path
import json
from datetime import datetime

print("=== V2 STARTING BALANCE HARD-CODE FIX ===")

# ------------------------------------------------------------
# 1) Correct the paper account file again
# ------------------------------------------------------------

account_path = Path("data_v2/v2_paper_account.json")
account = json.loads(account_path.read_text(encoding="utf-8"))

backup_account = Path("data_v2/v2_paper_account_BACKUP_BEFORE_FINAL_20000_BALANCE_FIX.json")
backup_account.write_text(json.dumps(account, indent=2), encoding="utf-8")

for key in [
    "starting_balance",
    "initial_balance",
    "starting_cash",
    "initial_cash",
    "paper_starting_balance",
    "original_starting_balance",
    "original_balance",
]:
    account[key] = 20000.0

account["updated_at"] = datetime.now().isoformat(timespec="seconds")

actions = account.get("actions")
if not isinstance(actions, list):
    actions = []

actions.append({
    "time": datetime.now().isoformat(timespec="seconds"),
    "action": "FINAL_STARTING_BALANCE_20000_FIX",
    "new_starting_balance": 20000.0,
    "reason": "Correct shared V2 paper monitor after adding $10,000 paper cash. Starting balance should be $20,000.",
    "source": "owner_manual_final_monitor_fix",
})

account["actions"] = actions
account_path.write_text(json.dumps(account, indent=2), encoding="utf-8")

print("Updated v2_paper_account.json starting balance fields to 20000.")

# ------------------------------------------------------------
# 2) Correct V2 settings if monitor/status reads from settings
# ------------------------------------------------------------

settings_path = Path("data_v2/v2_settings.json")
if settings_path.exists():
    settings = json.loads(settings_path.read_text(encoding="utf-8"))

    backup_settings = Path("data_v2/v2_settings_BACKUP_BEFORE_FINAL_20000_BALANCE_FIX.json")
    backup_settings.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    for key in [
        "starting_balance",
        "paper_starting_balance",
        "initial_balance",
        "initial_cash",
        "original_starting_balance",
        "v2_starting_balance",
    ]:
        settings[key] = 20000.0

    settings["updated_at"] = datetime.now().isoformat(timespec="seconds")
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    print("Updated v2_settings.json starting balance fields to 20000.")
else:
    print("No data_v2/v2_settings.json found; skipped settings update.")

# ------------------------------------------------------------
# 3) Patch likely hardcoded shared-account monitor/status fallbacks
#    Avoid touching engine account reconstruction files.
# ------------------------------------------------------------

paths = []
paths.extend(Path("alientai_v2").glob("*.py"))
paths.append(Path("main.py"))

patterns = [
    ("Original V2 paper balance", "Original V2 paper balance"),
    ("starting_balance", "starting_balance"),
    ("Starting Balance", "Starting Balance"),
    ("total_pnl", "total_pnl"),
    ("account_value", "account_value"),
]

replace_pairs = [
    ("starting_balance = 10000.0", "starting_balance = 20000.0"),
    ("starting_balance = 10000", "starting_balance = 20000"),
    ("starting_balance': 10000.0", "starting_balance': 20000.0"),
    ("starting_balance': 10000", "starting_balance': 20000"),
    ('starting_balance": 10000.0', 'starting_balance": 20000.0'),
    ('starting_balance": 10000', 'starting_balance": 20000'),
    ("paper_starting_balance = 10000.0", "paper_starting_balance = 20000.0"),
    ("paper_starting_balance = 10000", "paper_starting_balance = 20000"),
    ("initial_balance = 10000.0", "initial_balance = 20000.0"),
    ("initial_balance = 10000", "initial_balance = 20000"),
    ("STARTING_BALANCE = 10000.0", "STARTING_BALANCE = 20000.0"),
    ("STARTING_BALANCE = 10000", "STARTING_BALANCE = 20000"),
    ("V2_STARTING_BALANCE = 10000.0", "V2_STARTING_BALANCE = 20000.0"),
    ("V2_STARTING_BALANCE = 10000", "V2_STARTING_BALANCE = 20000"),
    ("|| 10000.0", "|| 20000.0"),
    ("|| 10000", "|| 20000"),
]

total_hits = 0

for path in paths:
    if not path.exists():
        continue

    # Do not alter engine account reconstruction; those separate research accounts should stay $10,000 each.
    if "engine_account" in path.name.lower() or "engine_accounts" in str(path).lower():
        continue

    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    original = text

    # Only patch files that appear to be related to V2 monitor/status/account display.
    if not any(p[0] in text for p in patterns):
        continue

    hits = 0
    for old, new in replace_pairs:
        if old in text:
            text = text.replace(old, new)
            hits += 1

    if hits:
        backup = path.with_name(path.stem + "_BACKUP_BEFORE_FINAL_20000_BALANCE_FIX" + path.suffix)
        backup.write_text(original, encoding="utf-8")
        path.write_text(text, encoding="utf-8")
        total_hits += hits
        print(f"Patched {path}: {hits} replacements; backup={backup}")

print("Total hardcoded/fallback replacements:", total_hits)

# ------------------------------------------------------------
# 4) Quick account math verification from file
# ------------------------------------------------------------

account = json.loads(account_path.read_text(encoding="utf-8"))
cash = float(account.get("cash") or 0)
starting = float(account.get("starting_balance") or 0)

print("")
print("VERIFY FILE VALUES")
print("starting_balance =", starting)
print("cash =", cash)
print("open_positions =", len(account.get("open_positions", {})))
print("")
print("Now run py_compile, rebuild accounts, restart server, and refresh monitor.")
