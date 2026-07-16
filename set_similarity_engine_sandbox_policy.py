import json
from pathlib import Path
from datetime import datetime

settings_path = Path("data_v2/v2_settings.json")
backup_path = Path("data_v2/v2_settings_BACKUP_BEFORE_SIMILARITY_SANDBOX_POLICY.json")

if not settings_path.exists():
    raise SystemExit("Missing data_v2/v2_settings.json")

settings = json.loads(settings_path.read_text(encoding="utf-8"))
backup_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

settings["similarity_engine_trained"] = True
settings["similarity_engine_training_source"] = "sp500_v1_loose_test"
settings["similarity_engine_model_path"] = "data_v2/similarity_engine_training/sp500_v1_loose_test/similarity_engine_model.json"
settings["similarity_engine_allowed_symbols_path"] = "data_v2/similarity_engine_training/sp500_v1_loose_test/similarity_engine_sandbox_allowed_symbols.txt"
settings["similarity_engine_candidate_report_path"] = "data_v2/similarity_engine_training/sp500_v1_loose_test/similarity_engine_sandbox_candidates_strict.csv"

# Important safety gates.
settings["similarity_engine_main_v2_buying_enabled"] = False
settings["similarity_engine_sandbox_enabled"] = True
settings["similarity_engine_sandbox_paper_only"] = True
settings["similarity_engine_sandbox_starting_balance"] = 10000.0
settings["similarity_engine_sandbox_max_position_dollars"] = 500.0
settings["similarity_engine_sandbox_max_open_positions"] = 9
settings["similarity_engine_sandbox_min_hold_days"] = 20
settings["similarity_engine_sandbox_score_threshold"] = 51.5
settings["similarity_engine_sandbox_watch_threshold"] = 50.8
settings["similarity_engine_sandbox_real_trading_enabled"] = False

settings["updated_at"] = datetime.now().isoformat(timespec="seconds")
settings["similarity_engine_note"] = (
    "Similarity engine trained from S&P daily feature library. "
    "It is approved for sandbox paper testing only, not main V2 buying. "
    "TDG excluded from sandbox because its buy signal was not selective."
)

settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

print("Similarity sandbox policy saved.")
print("Backup:", backup_path)
print("sandbox_enabled =", settings["similarity_engine_sandbox_enabled"])
print("main_v2_buying_enabled =", settings["similarity_engine_main_v2_buying_enabled"])
print("allowed_symbols_path =", settings["similarity_engine_allowed_symbols_path"])
