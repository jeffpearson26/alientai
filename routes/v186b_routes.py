from typing import Any

from research.engine_scorecard import scorecard_summary, get_or_create_scorecards


def install_v186b_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v186b/status")
    def alpha_v186b_status():
        cards = get_or_create_scorecards(state)
        return {
            "status": "success",
            "build": "ALIENTAI_V186B_SCORECARD_REPAIR",
            "message": "Scorecards are repaired and normalized.",
            "engine_count": len(cards),
            "routes": ["/alpha/scorecards/repair"],
        }

    @app.post("/alpha/scorecards/repair")
    def alpha_scorecards_repair():
        return {
            "status": "success",
            "scorecards": scorecard_summary(state),
        }

    return app
