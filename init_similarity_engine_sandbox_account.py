import json
from pathlib import Path
from datetime import datetime

BUILD = "ALIENTAI_V2_SIMILARITY_ENGINE_SANDBOX_ACCOUNT_INIT_V1"

PROJECT_ROOT = Path.cwd()

sandbox_dir = PROJECT_ROOT / "data_v2" / "similarity_engine_sandbox"
sandbox_dir.mkdir(parents=True, exist_ok=True)

account_path = sandbox_dir / "similarity_engine_sandbox_account.json"
backup_path = sandbox_dir / "similarity_engine_sandbox_account_BACKUP_BEFORE_REINIT.json"

allowed_path = PROJECT_ROOT / "data_v2" / "similarity_engine_training" / "sp500_v1_loose_test" / "similarity_engine_sandbox_allowed_symbols.txt"
candidate_report_path = PROJECT_ROOT / "data_v2" / "similarity_engine_training" / "sp500_v1_loose_test" / "similarity_engine_sandbox_candidates_strict.csv"
model_path = PROJECT_ROOT / "data_v2" / "similarity_engine_training" / "sp500_v1_loose_test" / "similarity_engine_model.json"

if not allowed_path.exists():
    raise SystemExit(f"Missing allowed symbols file: {allowed_path}")

allowed_symbols = [
    line.strip().upper()
    for line in allowed_path.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    if line.strip()
]

if not allowed_symbols:
    raise SystemExit("Allowed symbols file is empty.")

if account_path.exists():
    backup_path.write_text(account_path.read_text(encoding="utf-8"), encoding="utf-8")
    print("Existing sandbox account backed up to:", backup_path)

starting_balance = 10000.0

account = {
    "build": BUILD,
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "updated_at": datetime.now().isoformat(timespec="seconds"),

    "engine_id": "similarity_engine_sandbox",
    "engine_family": "similarity_engine",
    "mode": "paper_only_sandbox",
    "real_trading_enabled": False,
    "main_v2_buying_enabled": False,

    "starting_balance": starting_balance,
    "cash": starting_balance,
    "open_position_value": 0.0,
    "account_value": starting_balance,
    "realized_pnl": 0.0,
    "unrealized_pnl": 0.0,
    "total_pnl": 0.0,
    "total_pnl_pct": 0.0,

    "max_position_dollars": 500.0,
    "max_open_positions": 9,
    "min_hold_days": 20,
    "score_threshold": 51.5,
    "watch_threshold": 50.8,

    "allowed_symbols": allowed_symbols,
    "allowed_symbols_count": len(allowed_symbols),
    "allowed_symbols_path": str(allowed_path),
    "candidate_report_path": str(candidate_report_path),
    "model_path": str(model_path),

    "open_positions": {},
    "closed_trades": [],
    "actions": [
        {
            "time": datetime.now().isoformat(timespec="seconds"),
            "action": "INIT_SIMILARITY_SANDBOX_ACCOUNT",
            "amount": starting_balance,
            "reason": "Created separate paper-only sandbox account for trained S&P similarity engine.",
            "allowed_symbols": allowed_symbols,
        }
    ],

    "note": (
        "This is a separate paper-only sandbox account for the similarity engine. "
        "It is not allowed to place real trades and is not part of the main V2 buyer group."
    ),
}

account_path.write_text(json.dumps(account, indent=2), encoding="utf-8")

print("")
print("Similarity sandbox account initialized.")
print("Account path:", account_path)
print("Starting balance:", starting_balance)
print("Allowed symbols:", len(allowed_symbols))
print("")
for sym in allowed_symbols:
    print(" ", sym)
