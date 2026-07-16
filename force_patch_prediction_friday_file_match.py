from pathlib import Path

path = Path("train_v2_prediction_friday_from_daily.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("train_v2_prediction_friday_from_daily_BACKUP_BEFORE_FORCE_FILE_MATCH.py")
backup.write_text(text, encoding="utf-8")

start = text.find("def find_symbol_files(")
if start == -1:
    raise SystemExit("Could not find def find_symbol_files.")

end = text.find("\ndef main(", start)
if end == -1:
    raise SystemExit("Could not find def main after find_symbol_files.")

new_func = r'''def find_symbol_files(symbol_filter: Optional[List[str]]) -> List[Path]:
    """
    Find daily Schwab history files.

    Your downloaded files are named like:
      MARA_schwab_1d_max.csv
      AAPL_schwab_1d_max.csv

    This matcher uses the filename prefix before the first underscore as the ticker.
    """
    files = sorted(INPUT_DIR.rglob("*.csv"))

    if not symbol_filter:
        return files

    wanted = {str(s).upper().strip() for s in symbol_filter if str(s).strip()}
    matched: List[Path] = []

    for p in files:
        stem = p.stem.upper()
        file_ticker = stem.split("_", 1)[0].strip()

        if file_ticker in wanted:
            matched.append(p)

    return matched


'''

text = text[:start] + new_func + text[end + 1:]

path.write_text(text, encoding="utf-8")
print("Force-replaced find_symbol_files with Schwab prefix matcher.")
