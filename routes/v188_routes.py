from typing import Any

from research.pattern_discovery import run_pattern_discovery, pattern_discovery_summary


def install_v188_routes(app, bot_state: dict[str, Any] | None = None):
    @app.get("/alpha/v188/status")
    def alpha_v188_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V188_PATTERN_DISCOVERY_ENGINE",
            "message": "Pattern Discovery Engine is installed.",
            "summary": pattern_discovery_summary(),
            "routes": [
                "/alpha/patterns/discover",
                "/alpha/patterns/summary",
            ],
        }

    @app.get("/alpha/patterns/summary")
    def alpha_patterns_summary(min_count: int = 8):
        return pattern_discovery_summary(min_count=min_count)

    @app.get("/alpha/patterns/discover")
    def alpha_patterns_discover(min_count: int = 8, top_n: int = 25):
        return run_pattern_discovery(min_count=min_count, top_n=top_n)

    return app
