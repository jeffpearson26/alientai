from pathlib import Path

path = Path("train_v2_prediction_friday_sp500_from_daily.py")
text = path.read_text(encoding="utf-8-sig")

text = text.replace(
    'INPUT_DIR = PROJECT_ROOT / "data_v2" / "daily_schwab_max_history"',
    'INPUT_DIR = PROJECT_ROOT / "data_v2" / "sp500_daily_schwab_max_history"'
)

text = text.replace(
    'OUT_DIR = PROJECT_ROOT / "data_v2" / "prediction_friday_daily_training"',
    'OUT_DIR = PROJECT_ROOT / "data_v2" / "prediction_friday_sp500_daily_training"'
)

text = text.replace("prediction_friday_daily_records.jsonl", "prediction_friday_sp500_daily_records.jsonl")
text = text.replace("prediction_friday_daily_summary.csv", "prediction_friday_sp500_daily_summary.csv")
text = text.replace("prediction_friday_daily_summary.json", "prediction_friday_sp500_daily_summary.json")
text = text.replace("prediction_friday_symbol_policy.json", "prediction_friday_sp500_symbol_policy.json")
text = text.replace("prediction_friday_allow_symbols.txt", "prediction_friday_sp500_allow_symbols.txt")

text = text.replace(
    'BUILD = "ALIENTAI_V2_PREDICTION_FRIDAY_DAILY_TRAINER_V1"',
    'BUILD = "ALIENTAI_V2_PREDICTION_FRIDAY_SP500_DAILY_TRAINER_V1"'
)

path.write_text(text, encoding="utf-8")
print("Created S&P 500 Friday trainer.")
