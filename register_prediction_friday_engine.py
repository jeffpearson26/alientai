from pathlib import Path

path = Path("alientai_v2/engines/engine_registry.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/engines/engine_registry_BACKUP_BEFORE_PREDICTION_FRIDAY.py")
backup.write_text(text, encoding="utf-8")

if "run_prediction_friday" not in text:
    text = text.replace(
        "from alientai_v2.engines.prediction_20day import scan as run_prediction_20day",
        "from alientai_v2.engines.prediction_20day import scan as run_prediction_20day\nfrom alientai_v2.engines.prediction_friday import scan as run_prediction_friday",
        1,
    )

if '"prediction_friday": run_prediction_friday,' not in text:
    text = text.replace(
        '"prediction_20day": run_prediction_20day,',
        '"prediction_20day": run_prediction_20day,\n    "prediction_friday": run_prediction_friday,',
        1,
    )

path.write_text(text, encoding="utf-8")
print("Registered prediction_friday engine.")
