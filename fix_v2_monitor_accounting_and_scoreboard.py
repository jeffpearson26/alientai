from pathlib import Path
from datetime import datetime
import json

print("=== FIXING V2 MONITOR ACCOUNTING + ENGINE SCOREBOARD ===")

# ------------------------------------------------------------
# 1) Fix paper account balance fields
# ------------------------------------------------------------

account_path = Path("data_v2/v2_paper_account.json")
if not account_path.exists():
    raise SystemExit("Missing data_v2/v2_paper_account.json")

account = json.loads(account_path.read_text(encoding="utf-8"))
backup_account = Path("data_v2/v2_paper_account_BACKUP_BEFORE_MONITOR_20000_AND_SCOREBOARD_FIX.json")
backup_account.write_text(json.dumps(account, indent=2), encoding="utf-8")

old_values = {
    "starting_balance": account.get("starting_balance"),
    "initial_balance": account.get("initial_balance"),
    "starting_cash": account.get("starting_cash"),
    "initial_cash": account.get("initial_cash"),
    "paper_starting_balance": account.get("paper_starting_balance"),
}

# Set multiple likely fields so whichever field the monitor/status uses is corrected.
account["starting_balance"] = 20000.0
account["initial_balance"] = 20000.0
account["starting_cash"] = 20000.0
account["initial_cash"] = 20000.0
account["paper_starting_balance"] = 20000.0
account["updated_at"] = datetime.now().isoformat(timespec="seconds")

actions = account.get("actions")
if not isinstance(actions, list):
    actions = []

actions.append({
    "time": datetime.now().isoformat(timespec="seconds"),
    "action": "PAPER_ACCOUNTING_MONITOR_FIX",
    "old_values": old_values,
    "new_starting_balance": 20000.0,
    "reason": "Correct V2 monitor after adding another $10,000 paper cash. Prevent added paper capital from showing as profit.",
    "source": "owner_manual_monitor_fix"
})

account["actions"] = actions
account_path.write_text(json.dumps(account, indent=2), encoding="utf-8")

print("Fixed v2_paper_account.json paper starting balance fields.")
print("Account backup:", backup_account)

# ------------------------------------------------------------
# 2) Fix JavaScript pct() missing helper in v2_routes.py
# ------------------------------------------------------------

routes_path = Path("alientai_v2/v2_routes.py")
if not routes_path.exists():
    raise SystemExit("Missing alientai_v2/v2_routes.py")

text = routes_path.read_text(encoding="utf-8-sig")
backup_routes = Path("alientai_v2/v2_routes_BACKUP_BEFORE_MONITOR_20000_AND_SCOREBOARD_FIX.py")
backup_routes.write_text(text, encoding="utf-8")

pct_helper = r'''
function pct(value) {
  const n = Number(value || 0);
  if (!Number.isFinite(n)) return "";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(3)}%`;
}
'''

if "function pct(value)" not in text:
    marker = "function renderEngineAccounts(data) {"
    if marker in text:
        text = text.replace(marker, pct_helper + "\n" + marker, 1)
        print("Added pct() JavaScript helper before renderEngineAccounts().")
    else:
        print("WARNING: Could not find renderEngineAccounts(data). pct() was not added.")
else:
    print("pct() helper already exists.")

# ------------------------------------------------------------
# 3) Patch common hardcoded 10000 starting-balance fallback in monitor/status text
#    This is intentionally targeted to starting-balance wording only.
# ------------------------------------------------------------

targeted_replacements = [
    ('startingBalance || 10000', 'startingBalance || 20000'),
    ('startingBalance || 10000.0', 'startingBalance || 20000.0'),
    ('starting_balance || 10000', 'starting_balance || 20000'),
    ('starting_balance || 10000.0', 'starting_balance || 20000.0'),
    ('starting_balance = 10000.0', 'starting_balance = 20000.0'),
    ('starting_balance = 10000', 'starting_balance = 20000'),
    ('"starting_balance": 10000.0', '"starting_balance": 20000.0'),
    ('"starting_balance": 10000', '"starting_balance": 20000'),
    ("'starting_balance': 10000.0", "'starting_balance': 20000.0"),
    ("'starting_balance': 10000", "'starting_balance': 20000"),
]

hits = 0
for old, new in targeted_replacements:
    if old in text:
        text = text.replace(old, new)
        hits += 1

routes_path.write_text(text, encoding="utf-8")

print("Targeted starting-balance fallback replacements in v2_routes.py:", hits)
print("Routes backup:", backup_routes)

print("")
print("DONE.")
print("Next commands:")
print("python -m py_compile .\\alientai_v2\\v2_routes.py")
print("python -m py_compile .\\main.py")
print("python .\\build_v2_engine_accounts_v1.py")
print("python .\\show_engine_scoreboard.py")
