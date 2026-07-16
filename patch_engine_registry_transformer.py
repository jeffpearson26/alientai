from pathlib import Path

path = Path("alientai_v2/engines/engine_registry.py")
text = path.read_text(encoding="utf-8-sig")

# Add import if missing.
if "import transformer_20day" not in text:
    text = text.replace(
        "from alientai_v2.engines import prediction_20day, momentum_5min, similarity_engine",
        "from alientai_v2.engines import prediction_20day, momentum_5min, similarity_engine, transformer_20day",
    )

# Add to common registry styles.
if '"transformer_20day": transformer_20day.scan' not in text:
    text = text.replace(
        '"similarity_engine": similarity_engine.scan,',
        '"similarity_engine": similarity_engine.scan,\n    "transformer_20day": transformer_20day.scan,',
    )

if "'transformer_20day': transformer_20day.scan" not in text:
    text = text.replace(
        "'similarity_engine': similarity_engine.scan,",
        "'similarity_engine': similarity_engine.scan,\n    'transformer_20day': transformer_20day.scan,",
    )

path.write_text(text, encoding="utf-8")
