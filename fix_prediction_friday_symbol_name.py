from pathlib import Path

path = Path("train_v2_prediction_friday_from_daily.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("train_v2_prediction_friday_from_daily_BACKUP_BEFORE_SYMBOL_PREFIX_FIX.py")
backup.write_text(text, encoding="utf-8")

start = text.find("def symbol_from_file(")
if start == -1:
    raise SystemExit("Could not find def symbol_from_file.")

end = text.find("\ndef load_symbols_from_file", start)
if end == -1:
    raise SystemExit("Could not find def load_symbols_from_file after symbol_from_file.")

new_func = r'''def symbol_from_file(path: Path) -> str:
    """
    Extract ticker from your Schwab daily filenames.

    Your files look like:
      MARA_schwab_1d_max.csv
      AAPL_schwab_1d_max.csv

    So the ticker is the part before the first underscore.
    """
    stem = path.stem.upper().strip()
    if "_" in stem:
        return stem.split("_", 1)[0].strip()
    return stem


'''

text = text[:start] + new_func + text[end + 1:]

path.write_text(text, encoding="utf-8")
print("Fixed symbol_from_file to return ticker prefix only.")
