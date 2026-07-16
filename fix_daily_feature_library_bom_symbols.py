from pathlib import Path

path = Path("build_v2_daily_feature_library_v1.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("build_v2_daily_feature_library_v1_BACKUP_BEFORE_BOM_SYMBOL_FIX.py")
backup.write_text(text, encoding="utf-8")

old = '''        s = line.strip().upper()
        if not s or s.startswith("#"):
            continue
        if "," in s:
            s = s.split(",", 1)[0].strip().upper()
'''

new = '''        s = line.replace("\\ufeff", "").strip().upper()
        if not s or s.startswith("#"):
            continue
        if "," in s:
            s = s.split(",", 1)[0].replace("\\ufeff", "").strip().upper()
'''

if old not in text:
    raise SystemExit("Could not find read_symbols_file symbol-cleaning block.")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")

print("Fixed BOM/invisible-character cleanup in symbol reader.")
print("Backup:", backup)
