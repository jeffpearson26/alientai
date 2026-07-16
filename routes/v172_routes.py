from typing import Any

from history.ingredient_library import list_ingredients, ingredient_summary
from history.warehouse import get_or_create_warehouse
from history.context_builder import build_research_context
from research.evidence_vault import record_evidence, evidence_summary

def install_v172_routes(app, bot_state: dict[str, Any] | None = None):
    state = bot_state if bot_state is not None else {}

    @app.get("/alpha/v172/status")
    def alpha_v172_status():
        warehouse = get_or_create_warehouse(state)
        return {
            "status": "success",
            "build": "ALIENTAI_V172_WAREHOUSE_INGREDIENTS_CONTEXT",
            "warehouse": warehouse.status(),
            "ingredients": ingredient_summary(),
            "evidence_vault": evidence_summary(state),
        }

    @app.get("/alpha/ingredients")
    def alpha_ingredients():
        return {"status": "success", "summary": ingredient_summary(), "ingredients": list_ingredients()}

    @app.get("/alpha/context/{symbol}")
    def alpha_context(symbol: str):
        return {"status": "success", "context": build_research_context(symbol, state)}

    @app.post("/alpha/evidence/{program_id}/{symbol}")
    def alpha_record_evidence(program_id: str, symbol: str, decision: str = "OBSERVE", notes: str = ""):
        context = build_research_context(symbol, state)
        record = record_evidence(state, program_id, symbol, decision, context, notes)
        return {"status": "success", "record": record, "summary": evidence_summary(state)}

    @app.get("/alpha/evidence")
    def alpha_evidence():
        return {"status": "success", "summary": evidence_summary(state), "records": state.get("evidence_vault", [])[-25:]}

    return app
