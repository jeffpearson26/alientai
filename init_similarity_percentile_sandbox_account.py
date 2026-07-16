import json
from pathlib import Path
from datetime import datetime

BUILD = "ALIENTAI_V2_SIMILARITY_PERCENTILE_SANDBOX_ACCOUNT_INIT_V1"

root = Path.cwd()

sandbox_dir = root / "data_v2" / "similarity_percentile_sandbox"
sandbox_dir.mkdir(parents=True, exist_ok=True)

account_path = sandbox_dir / "similarity_percentile_sandbox_account.json"
backup_path = sandbox_dir / "similarity_percentile_sandbox_account_BACKUP_BEFORE_REINIT.json"

allowed_path = root / "data_v2" / "similarity_engine_training" / "sp500_percentile_v1" / "similarity_percentile_sandbox_allowed_symbols.txt"
thresholds_path = root / "data_v2" / "similarity_engine_training" / "sp500_percentile_v1" / "similarity_percentile_sandbox_thresholds.json"
model_path = root / "data_v2" / "similarity_engine_training" / "sp500_v1_loose_test" / "similarity_engine_model.json"

if not allowed_path.exists():
    raise SystemExit(f"Missing allowed symbols file: {allowed_path}")

if not thresholds_path.exists():
    raise SystemExit(f"Missing thresholds file: {thresholds_path}")

allowed_symbols = [
    line.strip().upper()
    for line in allowed_path.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    if line.strip()
]

thresholds = json.loads(thresholds_path.read_text(encoding="utf-8"))

if account_path.exists():
    backup_path.write_text(account_path.read_text(encoding="utf-8"), encoding="utf-8")
    print("Existing percentile sandbox account backed up to:", backup_path)

starting_balance = 10000.0

account = {
    "build": BUILD,
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "updated_at": datetime.now().isoformat(timespec="seconds"),

    "engine_id": "similarity_percentile_sandbox",
    "engine_family": "similarity_engine",
    "mode": "paper_only_percentile_sandbox",
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
    "max_open_positions": min(len(allowed_symbols), 12),
    "min_hold_days": 20,

    "threshold_mode": "symbol_specific_top10_score_threshold",
    "fallback_score_threshold": 51.5,

    "allowed_symbols": allowed_symbols,
    "allowed_symbols_count": len(allowed_symbols),
    "allowed_symbols_path": str(allowed_path),
    "thresholds_path": str(thresholds_path),
    "model_path": str(model_path),

    "open_positions": {},
    "closed_trades": [],
    "actions": [
        {
            "time": datetime.now().isoformat(timespec="seconds"),
            "action": "INIT_SIMILARITY_PERCENTILE_SANDBOX_ACCOUNT",
            "amount": starting_balance,
            "reason": "Created separate paper-only percentile sandbox account for strict S&P similarity percentile candidates.",
            "allowed_symbols": allowed_symbols,
            "threshold_mode": "symbol_specific_top10_score_threshold",
        }
    ],

    "note": (
        "This is a separate paper-only sandbox account for the percentile-calibrated similarity engine. "
        "It uses each symbol's own top10_score_threshold. It does not touch main V2 and cannot place real trades."
    ),
}

account_path.write_text(json.dumps(account, indent=2), encoding="utf-8")

print("")
print("Similarity percentile sandbox account initialized.")
print("Account path:", account_path)
print("Starting balance:", starting_balance)
print("Allowed symbols:", len(allowed_symbols))
print("Threshold records:", thresholds.get("symbol_count"))
print("")
for sym in allowed_symbols:
    t = thresholds.get("symbols", {}).get(sym, {})
    print(sym, "threshold=", t.get("top10_score_threshold"), "win%=", t.get("top10_win_rate_pct"))
