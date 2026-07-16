from typing import Any

from research.learning_ledger import (
    ledger_summary,
    recent_records,
    record_recommendation,
    complete_record,
)
from research.engine_evaluator import engine_performance_from_ledger, apply_suggested_reliability

try:
    from research.parliament import analyze_symbol_parliament
except Exception:
    analyze_symbol_parliament = None

try:
    from research.director import analyze_symbol
except Exception:
    analyze_symbol = None


def install_v184_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v184/status")
    def alpha_v184_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V184_LEARNING_LEDGER",
            "message": "Engine learning ledger and evaluator are installed.",
            "summary": ledger_summary(),
            "routes": [
                "/alpha/learn/record/{symbol}",
                "/alpha/learn/ledger",
                "/alpha/learn/complete/{record_id}",
                "/alpha/learn/evaluate-engines",
                "/alpha/learn/apply-reliability",
            ],
        }

    @app.post("/alpha/learn/record/{symbol}")
    def alpha_learn_record(symbol: str, source: str = "parliament"):
        if source == "parliament" and analyze_symbol_parliament is not None:
            report = analyze_symbol_parliament(symbol, state)
        elif analyze_symbol is not None:
            report = analyze_symbol(symbol, state)
        else:
            return {"status": "error", "message": "No director/parliament analyzer is available."}

        return record_recommendation(report)

    @app.get("/alpha/learn/ledger")
    def alpha_learn_ledger(limit: int = 20):
        return recent_records(limit=limit)

    @app.post("/alpha/learn/complete/{record_id}")
    def alpha_learn_complete(record_id: str, return_pct: float | None = None, outcome: str | None = None, exit_price: float | None = None, notes: str | None = None):
        return complete_record(
            record_id=record_id,
            exit_price=exit_price,
            return_pct=return_pct,
            outcome=outcome,
            notes=notes,
        )

    @app.get("/alpha/learn/evaluate-engines")
    def alpha_learn_evaluate_engines():
        return engine_performance_from_ledger()

    @app.post("/alpha/learn/apply-reliability")
    def alpha_learn_apply_reliability():
        return apply_suggested_reliability(state)

    return app
