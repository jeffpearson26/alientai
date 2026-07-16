from typing import Any

from research_brain.fast_morning_runner import fast_morning_research


def install_v203b_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v203b/status")
    def alpha_v203b_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V203B_FAST_MORNING_RUNNER",
            "message": "Fast Morning Runner is installed.",
            "routes": [
                "/alpha/morning/fast-run",
            ],
        }

    @app.post("/alpha/morning/fast-run")
    def alpha_morning_fast_run(max_symbols: int = 50, deep_analyze_top: int = 5, record_buys: bool = False):
        return fast_morning_research(
            state,
            max_symbols=max_symbols,
            deep_analyze_top=deep_analyze_top,
            record_buys=record_buys,
        )

    return app
