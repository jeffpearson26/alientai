from typing import Any

from research.director import analyze_symbol, director_status
from research.engine_scorecard import scorecard_summary
from research.report_generator import generate_text_report


def install_v181_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v181/status")
    def alpha_v181_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V181_RESEARCH_DIRECTOR",
            "message": "Research Director subsystem is installed.",
            "routes": [
                "/alpha/director/{symbol}",
                "/alpha/report/{symbol}",
                "/alpha/engine-scorecards",
            ],
            "director": director_status(state),
        }

    @app.get("/alpha/director/{symbol}")
    def alpha_director(symbol: str):
        return analyze_symbol(symbol, state)

    @app.get("/alpha/report/{symbol}")
    def alpha_report(symbol: str):
        report = analyze_symbol(symbol, state)
        return generate_text_report(report)

    @app.get("/alpha/engine-scorecards")
    def alpha_engine_scorecards():
        return {
            "status": "success",
            "scorecards": scorecard_summary(state),
        }

    return app
