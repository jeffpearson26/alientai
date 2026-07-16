"""
AlientAI Route Loader V170B

Keeps main.py from collecting endless feature bridges.
Future route modules are loaded here.
"""

from __future__ import annotations

from typing import Any


def install_all_routes(app, bot_state: dict[str, Any] | None = None):
    installed = []
    skipped = []
    state = bot_state if bot_state is not None else {}

    try:
        from research.routes import install_research_routes
        install_research_routes(app, state)
        installed.append("research.routes")
    except Exception as exc:
        skipped.append({"module": "research.routes", "error": str(exc)})


    try:
        from routes.alpha_routes import install_alpha_routes
        install_alpha_routes(app, state)
        installed.append("routes.alpha_routes")
    except Exception as exc:
        skipped.append({"module": "routes.alpha_routes", "error": str(exc)})


    try:
        from routes.v172_routes import install_v172_routes
        install_v172_routes(app, state)
        installed.append("routes.v172_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v172_routes", "error": str(exc)})


    try:
        from routes.v173_routes import install_v173_routes
        install_v173_routes(app, state)
        installed.append("routes.v173_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v173_routes", "error": str(exc)})


    try:
        from routes.v174_routes import install_v174_routes
        install_v174_routes(app, state)
        installed.append("routes.v174_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v174_routes", "error": str(exc)})


    try:
        from routes.v175_routes import install_v175_routes
        install_v175_routes(app, state)
        installed.append("routes.v175_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v175_routes", "error": str(exc)})


    try:
        from routes.v176_routes import install_v176_routes
        install_v176_routes(app, state)
        installed.append("routes.v176_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v176_routes", "error": str(exc)})


    try:
        from routes.v181_routes import install_v181_routes
        install_v181_routes(app, state)
        installed.append("routes.v181_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v181_routes", "error": str(exc)})


    try:
        from routes.v182_routes import install_v182_routes
        install_v182_routes(app, state)
        installed.append("routes.v182_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v182_routes", "error": str(exc)})


    try:
        from routes.v183_routes import install_v183_routes
        install_v183_routes(app, state)
        installed.append("routes.v183_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v183_routes", "error": str(exc)})


    try:
        from routes.v184_routes import install_v184_routes
        install_v184_routes(app, state)
        installed.append("routes.v184_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v184_routes", "error": str(exc)})


    try:
        from routes.v185_routes import install_v185_routes
        install_v185_routes(app, state)
        installed.append("routes.v185_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v185_routes", "error": str(exc)})


    try:
        from routes.v186_routes import install_v186_routes
        install_v186_routes(app, state)
        installed.append("routes.v186_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v186_routes", "error": str(exc)})


    try:
        from routes.v186b_routes import install_v186b_routes
        install_v186b_routes(app, state)
        installed.append("routes.v186b_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v186b_routes", "error": str(exc)})


    try:
        from routes.v187_routes import install_v187_routes
        install_v187_routes(app, state)
        installed.append("routes.v187_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v187_routes", "error": str(exc)})


    try:
        from routes.v187b_routes import install_v187b_routes
        install_v187b_routes(app, state)
        installed.append("routes.v187b_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v187b_routes", "error": str(exc)})


    try:
        from routes.v188_routes import install_v188_routes
        install_v188_routes(app, state)
        installed.append("routes.v188_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v188_routes", "error": str(exc)})


    try:
        from routes.v201_routes import install_v201_routes
        install_v201_routes(app, state)
        installed.append("routes.v201_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v201_routes", "error": str(exc)})


    try:
        from routes.v202_routes import install_v202_routes
        install_v202_routes(app, state)
        installed.append("routes.v202_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v202_routes", "error": str(exc)})


    try:
        from routes.v203_routes import install_v203_routes
        install_v203_routes(app, state)
        installed.append("routes.v203_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v203_routes", "error": str(exc)})


    try:
        from routes.v203b_routes import install_v203b_routes
        install_v203b_routes(app, state)
        installed.append("routes.v203b_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v203b_routes", "error": str(exc)})


    try:
        from routes.v203c_routes import install_v203c_routes
        install_v203c_routes(app, state)
        installed.append("routes.v203c_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v203c_routes", "error": str(exc)})


    try:
        from routes.v203d_routes import install_v203d_routes
        install_v203d_routes(app, state)
        installed.append("routes.v203d_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v203d_routes", "error": str(exc)})


    try:
        from routes.v203e_routes import install_v203e_routes
        install_v203e_routes(app, state)
        installed.append("routes.v203e_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v203e_routes", "error": str(exc)})


    try:
        from routes.v204_routes import install_v204_routes
        install_v204_routes(app, state)
        installed.append("routes.v204_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v204_routes", "error": str(exc)})


    try:
        from routes.v205_routes import install_v205_routes
        install_v205_routes(app, state)
        installed.append("routes.v205_routes")
    except Exception as exc:
        skipped.append({"module": "routes.v205_routes", "error": str(exc)})


    try:
        from routes.public_v2_routes import router as public_v2_router
        app.include_router(public_v2_router)
        installed.append("routes.public_v2_routes")
    except Exception as exc:
        skipped.append({"module": "routes.public_v2_routes", "error": str(exc)})

    @app.get("/refactor/v170/status")
    def refactor_v170_status():
        return {
            "status": "success",
            "build": "ALIENTAI_V170B_ROUTE_LOADER_FOUNDATION",
            "message": "Route loader foundation is installed.",
            "installed_routes": installed,
            "skipped_routes": skipped,
        }

    return {"installed": installed, "skipped": skipped}
