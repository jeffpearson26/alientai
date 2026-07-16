from typing import Any

from research.parliament import analyze_symbol_parliament


def install_v183_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v183/status")
    def alpha_v183_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V183_RESEARCH_PARLIAMENT",
            "message": "Research Parliament is installed.",
            "routes": ["/alpha/parliament/{symbol}"],
            "engines_added": [
                "PULLBACK_RECOVERY_V183",
                "RELATIVE_STRENGTH_V183",
                "VOLUME_PRESSURE_V183",
                "RISK_GUARD_V183",
                "MARKET_REGIME_V183",
            ],
        }

    @app.get("/alpha/parliament/{symbol}")
    def alpha_parliament(symbol: str):
        return analyze_symbol_parliament(symbol, state)

    return app
