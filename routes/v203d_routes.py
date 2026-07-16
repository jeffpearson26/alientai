from typing import Any

from research_brain.direct_history_morning_runner import run_direct_history_morning


def install_v203d_routes(app, bot_state: dict[str, Any] | None = None):
    @app.get("/alpha/v203d/status")
    def alpha_v203d_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V203D_DIRECT_HISTORY_MORNING_RUNNER",
            "message": "Direct History Morning Runner is installed.",
            "routes": ["/alpha/morning/direct-history"],
        }

    @app.post("/alpha/morning/direct-history")
    def alpha_morning_direct_history(max_symbols: int = 250, daily_limit: int = 260):
        return run_direct_history_morning(max_symbols=max_symbols, daily_limit=daily_limit)

    return app
