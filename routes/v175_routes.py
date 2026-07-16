from typing import Any

from research.similarity_full import find_similar_history_full


def install_v175_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v175/status")
    def alpha_v175_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V175_FULL_SUPABASE_SIMILARITY",
            "message": "Full Supabase historical similarity search is installed.",
            "routes": ["/alpha/similarity-full/{symbol}"],
        }

    @app.get("/alpha/similarity-full/{symbol}")
    def alpha_similarity_full(symbol: str, top_n: int = 20, sample_step: int = 3):
        return find_similar_history_full(symbol, state, top_n=top_n, sample_step=sample_step)

    return app
