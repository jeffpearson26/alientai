from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List


from alientai_v2.engines.momentum_5min import scan as run_momentum_5min
from alientai_v2.engines.prediction_20day import scan as run_prediction_20day
from alientai_v2.engines.prediction_friday import scan as run_prediction_friday
from alientai_v2.engines.similarity_engine import run as run_similarity_engine
from alientai_v2.engines.transformer_20day import scan as run_transformer_20day
from alientai_v2.engines.options_research import scan as run_options_research
from alientai_v2.engines.rcef_engine import scan as run_rcef_research
from alientai_v2.engines.contextual_options_paper import scan as run_contextual_options_paper
from alientai_v2.engines.nasdaq100_technical_paper import scan as run_nasdaq100_technical_paper


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREDICTION_20DAY_POLICY_PATH = (
    PROJECT_ROOT
    / "data_v2"
    / "prediction_20day_daily_training"
    / "prediction_20day_symbol_policy.json"
)


ENGINE_RUNNERS: Dict[str, Callable[[List[Dict[str, Any]], Dict[str, Any]], List[Dict[str, Any]]]] = {
    "momentum_5min": run_momentum_5min,
    "prediction_20day": run_prediction_20day,
    "prediction_friday": run_prediction_friday,
    "similarity_engine": run_similarity_engine,
    "transformer_20day": run_transformer_20day,
    "options_research": run_options_research,
    "rcef_research": run_rcef_research,
    "contextual_options_shadow_v1": run_contextual_options_paper,
    "nasdaq100_technical_clone_v1": run_nasdaq100_technical_paper,
}


def available_engines() -> List[str]:
    return sorted(ENGINE_RUNNERS.keys())


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def load_prediction_20day_policy() -> Dict[str, Any]:
    if not PREDICTION_20DAY_POLICY_PATH.exists():
        return {
            "source": str(PREDICTION_20DAY_POLICY_PATH),
            "available": False,
            "allow_symbols": [],
            "watch_only_symbols": [],
            "block_symbols": [],
        }

    try:
        policy = json.loads(PREDICTION_20DAY_POLICY_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return {
            "source": str(PREDICTION_20DAY_POLICY_PATH),
            "available": False,
            "allow_symbols": [],
            "watch_only_symbols": [],
            "block_symbols": [],
        }

    policy["available"] = True
    policy["source"] = str(PREDICTION_20DAY_POLICY_PATH)
    return policy


def symbol_policy_for_prediction_20day(symbol: str, policy: Dict[str, Any]) -> str:
    symbol = str(symbol or "").upper().strip()

    allow = set(str(s).upper().strip() for s in policy.get("allow_symbols", []))
    watch_only = set(str(s).upper().strip() for s in policy.get("watch_only_symbols", []))
    block = set(str(s).upper().strip() for s in policy.get("block_symbols", []))

    if symbol in allow:
        return "ALLOW_BUY"

    if symbol in watch_only:
        return "WATCH_ONLY"

    if symbol in block:
        return "BLOCK_BUY"

    return "UNTRAINED"


def apply_prediction_20day_policy(rows: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Applies daily-trained 20-day policy to live prediction_20day candidates.

    This does not touch paper account state.
    It only changes candidate rows before the portfolio manager sees them.
    """
    policy_enabled = bool(settings.get("prediction_20day_daily_policy_enabled", True))

    if not policy_enabled:
        return rows

    policy = load_prediction_20day_policy()

    for row in rows:
        if not isinstance(row, dict):
            continue

        engine_id = str(row.get("engine_id") or "").strip()

        if engine_id != "prediction_20day":
            continue

        symbol = str(row.get("symbol") or "").upper().strip()
        symbol_policy = symbol_policy_for_prediction_20day(symbol, policy)

        original_decision = str(row.get("decision") or "")
        original_score = safe_float(row.get("score"), 0.0)

        row["prediction_20day_daily_policy"] = symbol_policy
        row["prediction_20day_daily_policy_source"] = policy.get("source")
        row["prediction_20day_original_decision"] = original_decision
        row["prediction_20day_original_score"] = original_score

        reason = str(row.get("reason") or "")

        if symbol_policy == "BLOCK_BUY":
            if original_decision == "BUY_CANDIDATE":
                row["decision"] = "AVOID"
                row["score"] = min(original_score, 5.0)
                row["reason"] = (
                    reason
                    + " Daily 20-day policy=BLOCK_BUY; live buy downgraded to AVOID."
                ).strip()

        elif symbol_policy == "WATCH_ONLY":
            if original_decision == "BUY_CANDIDATE":
                row["decision"] = "WATCH"
                row["score"] = min(original_score, 50.0)
                row["reason"] = (
                    reason
                    + " Daily 20-day policy=WATCH_ONLY; live buy downgraded to WATCH."
                ).strip()

        elif symbol_policy == "ALLOW_BUY":
            row["reason"] = (
                reason
                + " Daily 20-day policy=ALLOW_BUY."
            ).strip()

        else:
            # Untrained symbols should not become 20-day buys unless explicitly allowed.
            allow_untrained = bool(settings.get("prediction_20day_allow_untrained_buys", False))

            if original_decision == "BUY_CANDIDATE" and not allow_untrained:
                row["decision"] = "WATCH"
                row["score"] = min(original_score, 50.0)
                row["reason"] = (
                    reason
                    + " Daily 20-day policy=UNTRAINED; live buy downgraded to WATCH."
                ).strip()

    return rows


def run_enabled_engines(quotes: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    enabled = settings.get("enabled_engines")

    if not enabled:
        enabled = ["prediction_20day", "momentum_5min"]

    results: List[Dict[str, Any]] = []

    for engine_id in enabled:
        engine_id = str(engine_id or "").strip()

        runner = ENGINE_RUNNERS.get(engine_id)

        if runner is None:
            continue

        try:
            engine_rows = runner(quotes, settings)

            if not engine_rows:
                continue

            for row in engine_rows:
                if isinstance(row, dict):
                    row.setdefault("engine_id", engine_id)
                    results.append(row)

        except Exception as exc:
            results.append({
                "engine_id": engine_id,
                "symbol": "",
                "side": "LONG",
                "score": 0.0,
                "decision": "AVOID",
                "price": 0.0,
                "reason": f"{engine_id} engine error: {exc}",
                "source": engine_id,
            })

    results = apply_prediction_20day_policy(results, settings)

    results.sort(key=lambda r: safe_float(r.get("score"), 0.0), reverse=True)

    return results
