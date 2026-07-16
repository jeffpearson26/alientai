from typing import Any

from history.context_builder import build_research_context
from research.feature_snapshot import make_feature_snapshot
from research.similarity_engine import find_similar_history

def install_v174_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v174/status")
    def alpha_v174_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V174_HISTORICAL_SIMILARITY_ENGINE",
            "message": "Historical similarity engine is installed.",
            "routes": ["/alpha/snapshot/{symbol}", "/alpha/similarity/{symbol}"],
        }

    @app.get("/alpha/snapshot/{symbol}")
    def alpha_snapshot(symbol: str):
        context = build_research_context(symbol, state)
        return {"status": "success", "snapshot": make_feature_snapshot(context)}

    @app.get("/alpha/similarity/{symbol}")
    def alpha_similarity(symbol: str, top_n: int = 20, sample_step: int = 5):
        return find_similar_history(symbol, state, top_n=top_n, sample_step=sample_step)

    return app
