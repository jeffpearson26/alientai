from typing import Any

from history.data_pipeline_manager import (
    initialize_pipeline,
    load_pipeline_state,
    pipeline_summary,
    run_pipeline_batch,
    reset_problem_tasks,
)


def install_v173_routes(app, bot_state: dict[str, Any] | None = None):
    @app.get("/alpha/v173/status")
    def alpha_v173_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V173_DATA_PIPELINE_MANAGER",
            "summary": initialize_pipeline(),
        }

    @app.get("/alpha/v173/tasks")
    def alpha_v173_tasks():
        state = load_pipeline_state()
        return {
            "status": "success",
            "summary": pipeline_summary(state),
            "tasks": list(state.get("tasks", {}).values()),
        }

    @app.post("/alpha/v173/run-batch")
    def alpha_v173_run_batch(max_tasks: int = 5):
        return run_pipeline_batch(max_tasks=max_tasks)

    @app.post("/alpha/v173/reset-problem-tasks")
    def alpha_v173_reset_problem_tasks():
        return {
            "status": "success",
            "summary": reset_problem_tasks(),
        }

    return app
