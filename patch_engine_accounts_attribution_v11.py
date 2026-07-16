from pathlib import Path

path = Path("build_v2_engine_accounts_v1.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("build_v2_engine_accounts_v1_BACKUP_BEFORE_ATTRIBUTION_V11.py")
backup.write_text(text, encoding="utf-8")

old = '''def normalize_engine_id(value):
    engine = str(value or "").strip()
    if not engine:
        return "unknown_engine"
    return engine
'''

new = '''def normalize_engine_id(value):
    engine = str(value or "").strip()
    if not engine:
        return "unknown_engine"
    return engine


def infer_engine_id_from_row(row):
    """
    Better engine attribution for old positions/trades that were saved before
    every paper position had a clean engine_id.

    Rules:
    - Explicit engine_id wins.
    - Known strategy source wins.
    - Blank engine + 20-day horizon -> prediction_20day.
    - Blank engine + 5-day horizon -> prediction_friday.
    - Blank engine + 1-day horizon -> similarity_engine.
    - Build/app runner labels are not real engines unless no better clue exists.
    """
    explicit = str(row.get("engine_id") or row.get("engine") or "").strip()
    if explicit:
        return explicit

    source = str(row.get("source") or "").strip()

    known_sources = {
        "prediction_friday",
        "prediction_20day",
        "momentum_5min",
        "similarity_engine",
        "transformer_20day",
        "options_research",
    }

    if source in known_sources:
        return source

    horizon = safe_float(
        row.get("prediction_horizon_days")
        or row.get("horizon_days")
        or row.get("prediction_days"),
        0.0,
    )

    min_hold = safe_float(row.get("minimum_hold_minutes") or row.get("min_hold_minutes"), 0.0)

    # 20 trading days in the current V2 system is stored as 28800 minutes.
    if abs(horizon - 20.0) < 0.01 or min_hold >= 20000:
        return "prediction_20day"

    if abs(horizon - 5.0) < 0.01:
        return "prediction_friday"

    if abs(horizon - 1.0) < 0.01:
        return "similarity_engine"

    if source and not source.startswith("ALIENTAI_V2_PAPER_ENGINE_DIRECT_RUNNER"):
        return source

    return "unknown_engine"
'''

if old not in text:
    raise SystemExit("Could not find normalize_engine_id block. No changes made.")

text = text.replace(old, new, 1)

text = text.replace(
    'engine = normalize_engine_id(pos.get("engine_id") or pos.get("engine") or pos.get("source"))',
    'engine = infer_engine_id_from_row(pos)'
)

text = text.replace(
    'engine = normalize_engine_id(trade.get("engine_id") or trade.get("engine") or trade.get("source"))',
    'engine = infer_engine_id_from_row(trade)'
)

path.write_text(text, encoding="utf-8")

print("Patched engine attribution V1.1.")
print("Backup:", backup)
