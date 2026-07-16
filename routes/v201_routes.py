from typing import Any

from research_brain.registry import research_brain_registry
from research_brain.health import research_brain_health
from research_brain.brain_map import architecture_map, next_refactor_plan


def install_v201_routes(app, bot_state: dict[str, Any] | None = None):
    @app.get("/alpha/v201/status")
    def alpha_v201_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V201_RESEARCH_BRAIN_CORE",
            "message": "Research Brain architecture core is installed.",
            "routes": [
                "/alpha/brain/registry",
                "/alpha/brain/health",
                "/alpha/brain/map",
                "/alpha/brain/refactor-plan",
            ],
        }

    @app.get("/alpha/brain/registry")
    def alpha_brain_registry():
        return {
            "status": "success",
            "registry": research_brain_registry(),
        }

    @app.get("/alpha/brain/health")
    def alpha_brain_health():
        return research_brain_health()

    @app.get("/alpha/brain/map")
    def alpha_brain_map():
        return architecture_map()

    @app.get("/alpha/brain/refactor-plan")
    def alpha_brain_refactor_plan():
        return next_refactor_plan()

    return app
