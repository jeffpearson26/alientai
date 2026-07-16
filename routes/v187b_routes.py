from typing import Any

from research.adaptive_director import analyze_symbol_adaptive, adaptive_director_text_report


def install_v187b_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v187b/status")
    def alpha_v187b_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V187B_ADAPTIVE_DIRECTOR_CALIBRATION",
            "message": "Adaptive Director calibration is installed. WAIT votes now reduce conviction.",
            "routes": [
                "/alpha/adaptive-director/{symbol}",
                "/alpha/adaptive-report/{symbol}",
                "/alpha/v187b/status",
            ],
        }

    return app
