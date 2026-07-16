from typing import Any

from research_brain.morning_runner import (
    run_morning_research,
    list_morning_reports,
    latest_morning_report,
)


def install_v203_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v203/status")
    def alpha_v203_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V203_MORNING_RESEARCH_RUNNER",
            "message": "Morning Research Runner is installed.",
            "routes": [
                "/alpha/morning/run",
                "/alpha/morning/latest",
                "/alpha/morning/reports",
            ],
        }

    @app.post("/alpha/morning/run")
    def alpha_morning_run(max_symbols: int = 25, record_buys: bool = False):
        return run_morning_research(state, max_symbols=max_symbols, record_buys=record_buys)

    @app.get("/alpha/morning/latest")
    def alpha_morning_latest():
        return latest_morning_report()

    @app.get("/alpha/morning/reports")
    def alpha_morning_reports(limit: int = 20):
        return list_morning_reports(limit=limit)

    return app
