from typing import Any

from research.cross_market_similarity import find_cross_market_similarity


def install_v176_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v176/status")
    def alpha_v176_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V176_CROSS_MARKET_SIMILARITY",
            "message": "Cross-market similarity search is installed.",
            "routes": ["/alpha/similarity-cross/{symbol}"],
        }

    @app.get("/alpha/similarity-cross/{symbol}")
    def alpha_similarity_cross(symbol: str, top_n: int = 30, sample_step: int = 5, max_symbols: int = 50):
        return find_cross_market_similarity(
            symbol=symbol,
            state=state,
            top_n=top_n,
            sample_step=sample_step,
            max_symbols=max_symbols,
        )

    return app
