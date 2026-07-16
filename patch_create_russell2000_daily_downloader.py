from pathlib import Path

path = Path("download_russell2000_daily_schwab_max.py")
text = path.read_text(encoding="utf-8-sig")

text = text.replace(
    'BUILD = "ALIENTAI_V2_SP500_DAILY_SCHWAB_MAX_DOWNLOADER_V1"',
    'BUILD = "ALIENTAI_V2_RUSSELL2000_DAILY_SCHWAB_MAX_DOWNLOADER_V1"'
)

text = text.replace(
    'OUT_DIR = PROJECT_ROOT / "data_v2" / "sp500_daily_schwab_max_history"',
    'OUT_DIR = PROJECT_ROOT / "data_v2" / "daily_schwab_max_history"'
)

text = text.replace(
    'SUMMARY_PATH = OUT_DIR / "sp500_daily_download_summary.json"',
    'SUMMARY_PATH = OUT_DIR / "russell2000_daily_download_summary.json"'
)

text = text.replace(
    'SYMBOLS_OUT_PATH = OUT_DIR / "sp500_symbols_used.txt"',
    'SYMBOLS_OUT_PATH = OUT_DIR / "russell2000_symbols_used.txt"'
)

path.write_text(text, encoding="utf-8")
print("Created Russell 2000 daily downloader.")
