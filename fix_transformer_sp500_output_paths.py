from pathlib import Path

path = Path("train_v2_transformer_20day_sp500_from_supabase.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("train_v2_transformer_20day_sp500_from_supabase_BACKUP_BEFORE_PATH_FIX.py")
backup.write_text(text, encoding="utf-8")

replacements = {
    'OUT_DIR = PROJECT_ROOT / "data_v2" / "transformer_20day"':
        'OUT_DIR = PROJECT_ROOT / "data_v2" / "transformer_20day_sp500_supabase_training"',

    '"transformer_20day_model.pt"':
        '"transformer_20day_sp500_model.pt"',

    '"transformer_20day_scaler.json"':
        '"transformer_20day_sp500_scaler.json"',

    '"transformer_20day_metrics.json"':
        '"transformer_20day_sp500_metrics.json"',

    '"transformer_20day_symbol_summary.json"':
        '"transformer_20day_sp500_symbol_summary.json"',

    '"transformer_20day_config.json"':
        '"transformer_20day_sp500_config.json"',
}

hits = 0
for old, new in replacements.items():
    if old in text:
        text = text.replace(old, new)
        hits += 1

path.write_text(text, encoding="utf-8")

print("Patched S&P transformer output paths.")
print("Replacement hits:", hits)
print("Backup:", backup)
