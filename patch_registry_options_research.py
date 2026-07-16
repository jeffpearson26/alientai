from pathlib import Path

path = Path("alientai_v2/engines/engine_registry.py")
text = path.read_text(encoding="utf-8-sig")

if "run_options_research" not in text:
    text = text.replace(
        "from alientai_v2.engines.transformer_20day import scan as run_transformer_20day",
        "from alientai_v2.engines.transformer_20day import scan as run_transformer_20day\nfrom alientai_v2.engines.options_research import scan as run_options_research",
    )

if '"options_research": run_options_research,' not in text:
    text = text.replace(
        '"transformer_20day": run_transformer_20day,',
        '"transformer_20day": run_transformer_20day,\n    "options_research": run_options_research,',
    )

path.write_text(text, encoding="utf-8")
print("Registered options_research engine.")
