from __future__ import annotations

from typing import Any

from research.engine_runtime import get_or_create_runtime_manager
from research.research_director import get_or_create_research_director


def install_alpha_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v171/status")
    def alpha_v171_status():
        runtime = get_or_create_runtime_manager(state)
        director = get_or_create_research_director(state)
        return {
            "status": "success",
            "build": "ALIENTAI_V171_ALPHA_ENGINE_RUNTIME",
            "message": "AlientAI V2 Alpha runtime foundation is installed.",
            "runtime": runtime.summary(),
            "research_director": director.summary(),
        }

    @app.get("/alpha/engines")
    def alpha_engines():
        runtime = get_or_create_runtime_manager(state)
        return {"status": "success", "runtime": runtime.summary(), "engines": runtime.list_engines()}

    @app.post("/alpha/engines/{engine_id}/start")
    def alpha_start_engine(engine_id: str):
        runtime = get_or_create_runtime_manager(state)
        return runtime.start_engine(engine_id)

    @app.post("/alpha/engines/{engine_id}/stop")
    def alpha_stop_engine(engine_id: str):
        runtime = get_or_create_runtime_manager(state)
        return runtime.stop_engine(engine_id)

    @app.post("/alpha/engines/{engine_id}/record-scan")
    def alpha_record_scan(engine_id: str):
        runtime = get_or_create_runtime_manager(state)
        return runtime.record_scan(engine_id)

    @app.get("/alpha/research-director/review")
    def alpha_research_director_review():
        runtime = get_or_create_runtime_manager(state)
        director = get_or_create_research_director(state)
        review = director.evaluate_runtime(runtime.summary())
        return {"status": "success", "review": review, "research_director": director.summary()}

    return app
