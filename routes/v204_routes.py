from pathlib import Path
from typing import Any


def install_v204_routes(app, bot_state: dict[str, Any] | None = None):
    @app.get("/alpha/v204/status")
    def alpha_v204_status():
        scripts = Path("scripts")
        logs = Path("morning_logs")
        return {
            "status": "success",
            "build": "ALIENTAI_V204B_MORNING_AUTOSTART_FIXED",
            "message": "Morning auto-start scripts are installed.",
            "task_name": "AlientAI Morning Research",
            "scheduled_time": "6:00 AM Pacific, Monday-Friday",
            "scripts": {
                "runner": str(scripts / "alientai_morning_autostart.ps1"),
                "install_task": str(scripts / "install_alientai_morning_task.ps1"),
                "uninstall_task": str(scripts / "uninstall_alientai_morning_task.ps1"),
            },
            "logs_folder": str(logs),
        }

    return app
