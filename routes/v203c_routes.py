from typing import Any

from research_brain.ultra_fast_morning_runner import ultra_fast_morning_research


def install_v203c_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v203c/status")
    def alpha_v203c_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V203C_ULTRA_FAST_MORNING_RUNNER",
            "message": "Ultra-Fast Morning Runner is installed.",
            "routes": [
                "/alpha/morning/ultra-fast",
            ],
        }

    @app.post("/alpha/morning/ultra-fast")
    def alpha_morning_ultra_fast(max_symbols: int = 250):
        return ultra_fast_morning_research(state, max_symbols=max_symbols)

    return app
