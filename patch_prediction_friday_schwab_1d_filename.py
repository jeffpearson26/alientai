from pathlib import Path

path = Path("train_v2_prediction_friday_from_daily.py")
text = path.read_text(encoding="utf-8-sig")

# Add the actual Schwab filename suffix used by your downloader:
# MARA_schwab_1d_max.csv
text = text.replace(
'''    for suffix in [
        "_DAILY_SCHWAB_MAX_HISTORY",
        "_SCHWAB_MAX_HISTORY",
        "_MAX_HISTORY",
        "_DAILY_HISTORY",
        "_DAILY_CANDLES",
        "_DAILY",
        "_HISTORY",
    ]:
''',
'''    for suffix in [
        "_SCHWAB_1D_MAX",
        "_DAILY_SCHWAB_MAX_HISTORY",
        "_SCHWAB_MAX_HISTORY",
        "_MAX_HISTORY",
        "_DAILY_HISTORY",
        "_DAILY_CANDLES",
        "_DAILY",
        "_HISTORY",
    ]:
'''
)

path.write_text(text, encoding="utf-8")
print("Added _SCHWAB_1D_MAX filename suffix support.")
