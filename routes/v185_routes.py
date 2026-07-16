from typing import Any

from research.historical_backfill import create_backfill_records


def install_v185_routes(app, bot_state: dict[str, Any] | None = None):
    @app.get("/alpha/v185/status")
    def alpha_v185_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V185_HISTORICAL_BACKFILL",
            "message": "Historical backfill evaluator is installed.",
            "routes": ["/alpha/learn/backfill"],
        }

    @app.post("/alpha/learn/backfill")
    def alpha_learn_backfill(max_symbols: int = 10, records_per_symbol: int = 10, hold_days: int = 10, step_days: int = 20):
        return create_backfill_records(
            max_symbols=max_symbols,
            records_per_symbol=records_per_symbol,
            hold_days=hold_days,
            step_days=step_days,
        )

    return app
