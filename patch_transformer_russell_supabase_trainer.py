from pathlib import Path

path = Path("train_v2_transformer_20day_russell_from_supabase.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("train_v2_transformer_20day_russell_from_supabase_BACKUP_BEFORE_OUTPUT_PATCH.py")
backup.write_text(text, encoding="utf-8")

replacements = {
    "ALIENTAI_V2_TRANSFORMER_20DAY_DAILY_TRAINER_V1":
        "ALIENTAI_V2_TRANSFORMER_20DAY_RUSSELL_SUPABASE_TRAINER_V1",

    "transformer_20day_daily_training":
        "transformer_20day_russell_supabase_training",

    "transformer_20day_daily_records.jsonl":
        "transformer_20day_russell_records.jsonl",

    "transformer_20day_daily_summary.csv":
        "transformer_20day_russell_summary.csv",

    "transformer_20day_daily_summary.json":
        "transformer_20day_russell_summary.json",

    "transformer_20day_symbol_policy.json":
        "transformer_20day_russell_symbol_policy.json",

    "transformer_20day_allow_symbols.txt":
        "transformer_20day_russell_allow_symbols.txt",
}

hits = 0
for old, new in replacements.items():
    if old in text:
        text = text.replace(old, new)
        hits += 1

path.write_text(text, encoding="utf-8")

print("Patched Russell transformer trainer.")
print("Replacement groups hit:", hits)
print("Backup:", backup)
