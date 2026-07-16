from typing import Any

from research.adaptive_reliability import (
    adaptive_reliability_preview,
    apply_adaptive_reliability,
    reset_adaptive_reliability,
)

try:
    from research.parliament import analyze_symbol_parliament
except Exception:
    analyze_symbol_parliament = None


def install_v186_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v186/status")
    def alpha_v186_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V186_ADAPTIVE_RELIABILITY",
            "message": "Adaptive reliability weighting is installed.",
            "routes": [
                "/alpha/reliability/preview",
                "/alpha/reliability/apply",
                "/alpha/reliability/reset",
                "/alpha/director-adaptive/{symbol}",
            ],
        }

    @app.get("/alpha/reliability/preview")
    def alpha_reliability_preview():
        return adaptive_reliability_preview(state)

    @app.post("/alpha/reliability/apply")
    def alpha_reliability_apply(min_buy_votes: int = 5):
        return apply_adaptive_reliability(state, min_buy_votes=min_buy_votes)

    @app.post("/alpha/reliability/reset")
    def alpha_reliability_reset():
        return reset_adaptive_reliability(state)

    @app.get("/alpha/director-adaptive/{symbol}")
    def alpha_director_adaptive(symbol: str):
        if analyze_symbol_parliament is None:
            return {"status": "error", "message": "Research Parliament is not available."}
        return analyze_symbol_parliament(symbol, state)

    return app
