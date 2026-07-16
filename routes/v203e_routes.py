from typing import Any

from research_brain.morning_command_center import freshness_status, run_morning_command_center


def install_v203e_routes(app, bot_state: dict[str, Any] | None = None):
    @app.get("/alpha/v203e/status")
    def alpha_v203e_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V203E_MORNING_COMMAND_CENTER",
            "message": "Morning Command Center is installed.",
            "routes": [
                "/alpha/morning/freshness",
                "/alpha/morning/command-center",
            ],
        }

    @app.get("/alpha/morning/freshness")
    def alpha_morning_freshness(max_symbols: int = 25, stale_days: int = 7):
        return freshness_status(max_symbols=max_symbols, stale_days=stale_days)

    @app.post("/alpha/morning/command-center")
    def alpha_morning_command_center(max_symbols: int = 25, stale_days: int = 7, allow_stale: bool = False, daily_limit: int = 260):
        return run_morning_command_center(
            max_symbols=max_symbols,
            stale_days=stale_days,
            allow_stale=allow_stale,
            daily_limit=daily_limit,
        )

    return app
