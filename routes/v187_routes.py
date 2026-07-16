from typing import Any

from research.adaptive_director import analyze_symbol_adaptive, adaptive_director_text_report


def install_v187_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v187/status")
    def alpha_v187_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V187_ADAPTIVE_RESEARCH_DIRECTOR",
            "message": "Adaptive Research Director is installed.",
            "routes": [
                "/alpha/adaptive-director/{symbol}",
                "/alpha/adaptive-report/{symbol}",
            ],
        }

    @app.get("/alpha/adaptive-director/{symbol}")
    def alpha_adaptive_director(symbol: str):
        return analyze_symbol_adaptive(symbol, state)

    @app.get("/alpha/adaptive-report/{symbol}")
    def alpha_adaptive_report(symbol: str):
        return adaptive_director_text_report(symbol, state)

    return app
