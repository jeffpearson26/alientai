from pathlib import Path

path = Path("alientai_v2/engines/engine_registry.py")
text = path.read_text(encoding="utf-8-sig")

old_import = '''from alientai_v2.engines.momentum_5min import scan as run_momentum_5min
from alientai_v2.engines.prediction_20day import scan as run_prediction_20day
from alientai_v2.engines.similarity_engine import run as run_similarity_engine
'''

new_import = '''from alientai_v2.engines.momentum_5min import scan as run_momentum_5min
from alientai_v2.engines.prediction_20day import scan as run_prediction_20day
from alientai_v2.engines.similarity_engine import run as run_similarity_engine
from alientai_v2.engines.transformer_20day import scan as run_transformer_20day
'''

if old_import not in text:
    raise SystemExit("Could not find the engine import block. Need manual patch.")

text = text.replace(old_import, new_import)

old_registry = '''ENGINE_RUNNERS: Dict[str, Callable[[List[Dict[str, Any]], Dict[str, Any]], List[Dict[str, Any]]]] = {
    "momentum_5min": run_momentum_5min,
    "prediction_20day": run_prediction_20day,
    "similarity_engine": run_similarity_engine,
}
'''

new_registry = '''ENGINE_RUNNERS: Dict[str, Callable[[List[Dict[str, Any]], Dict[str, Any]], List[Dict[str, Any]]]] = {
    "momentum_5min": run_momentum_5min,
    "prediction_20day": run_prediction_20day,
    "similarity_engine": run_similarity_engine,
    "transformer_20day": run_transformer_20day,
}
'''

if old_registry not in text:
    raise SystemExit("Could not find ENGINE_RUNNERS block. Need manual patch.")

text = text.replace(old_registry, new_registry)

path.write_text(text, encoding="utf-8")
