from typing import Any

from research_brain.adapters import (
    get_symbol_universe,
    build_feature_snapshot,
    run_adaptive_director,
    run_pattern_discovery,
    learning_summary,
    engine_evaluation,
)
from research_brain.snapshots import (
    research_brain_symbol_snapshot,
    research_brain_global_snapshot,
)


def install_v202_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v202/status")
    def alpha_v202_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V202_BRAIN_ADAPTERS",
            "message": "Stable Research Brain adapters are installed.",
            "routes": [
                "/alpha/brain/universe",
                "/alpha/brain/snapshot/{symbol}",
                "/alpha/brain/global",
                "/alpha/brain/feature/{symbol}",
                "/alpha/brain/adaptive/{symbol}",
                "/alpha/brain/patterns",
                "/alpha/brain/learning",
                "/alpha/brain/engines",
            ],
        }

    @app.get("/alpha/brain/universe")
    def alpha_brain_universe():
        return {"status": "success", "universe": get_symbol_universe()}

    @app.get("/alpha/brain/snapshot/{symbol}")
    def alpha_brain_symbol_snapshot(symbol: str):
        return research_brain_symbol_snapshot(symbol, state)

    @app.get("/alpha/brain/global")
    def alpha_brain_global_snapshot():
        return research_brain_global_snapshot(state)

    @app.get("/alpha/brain/feature/{symbol}")
    def alpha_brain_feature(symbol: str):
        return {"status": "success", "snapshot": build_feature_snapshot(symbol, state)}

    @app.get("/alpha/brain/adaptive/{symbol}")
    def alpha_brain_adaptive(symbol: str):
        return run_adaptive_director(symbol, state)

    @app.get("/alpha/brain/patterns")
    def alpha_brain_patterns(min_count: int = 8, top_n: int = 10):
        return run_pattern_discovery(min_count=min_count, top_n=top_n)

    @app.get("/alpha/brain/learning")
    def alpha_brain_learning():
        return {"status": "success", "learning": learning_summary()}

    @app.get("/alpha/brain/engines")
    def alpha_brain_engines():
        return engine_evaluation()

    return app
