from typing import Any

from history.symbol_discovery import get_research_universe_symbols


def install_v182_routes(app, bot_state: dict[str, Any] | None = None):
    @app.get("/alpha/v182/status")
    def alpha_v182_status():
        universe = get_research_universe_symbols()
        return {
            "status": "success",
            "build": "ALIENTAI_V182_SYMBOL_DISCOVERY_FIX",
            "message": "Research universe symbol discovery is installed.",
            "universe": universe,
            "routes": ["/alpha/research-universe"],
        }

    @app.get("/alpha/research-universe")
    def alpha_research_universe():
        return {
            "status": "success",
            "universe": get_research_universe_symbols(),
        }

    return app
