"""Public route wiring for AlientAI.

This module is presentation-only route assembly.

It does not execute the scanner, place paper trades, access Schwab,
modify account data, expose owner controls, or run ML scoring.
"""

from __future__ import annotations


PUBLIC_ROUTE_VERSION = "V168B_FIX_PUBLIC_ROUTES_QUOTE_ESCAPE"


PUBLIC_BASE_FUNCTION_ORDER = [
    "v163_build_public_page_html",
    "v162_build_public_page_html",
    "v161_build_public_page_html",
    "v160_build_public_page_html",
    "v158_build_active_public_page_html",
]


def get_best_public_base_html(main_globals: dict) -> str:
    """Call the latest available public-page builder from main.py globals.

    This is a transitional bridge. Later, the older V158-V163 public-page
    builders can also be moved out of main.py.
    """

    for fn_name in PUBLIC_BASE_FUNCTION_ORDER:
        fn = main_globals.get(fn_name)

        if callable(fn):
            try:
                html = fn()
                if html:
                    return html
            except Exception:
                pass

    return ""


def build_public_page_html(main_globals: dict) -> str:
    """Build the active public page HTML using module-based orbit visuals."""

    from web.public_orbit import wrap_first_hero_image

    html = get_best_public_base_html(main_globals)

    if not html:
        return ""

    return wrap_first_hero_image(html)


def public_page_status(main_globals: dict) -> dict:
    """Return public-page route/module status for diagnostics."""

    from web.public_orbit import ORBIT_SPEED_SECONDS, hero_satellite_overlay_html

    html = build_public_page_html(main_globals)
    overlay = hero_satellite_overlay_html()

    return {
        "status": "success",
        "refactor_version": PUBLIC_ROUTE_VERSION,
        "module": "routes.public_routes",
        "public_html_found": bool(html),
        "uses_public_orbit_module": True,
        "orbit_module": "web.public_orbit",
        "front_orbit_present": "v167-front-orbit" in html,
        "back_orbit_present": "v167-back-orbit" in html,
        "audio_button_present": "v167AudioControl" in html,
        "orbit_speed_seconds": ORBIT_SPEED_SECONDS,
        "orbit_overlay_length": len(overlay),
        "active_paths": ["/", "/public"],
        "main_py_public_route_role": "thin bridge only",
        "message": (
            "Active public page route assembly is module-based through "
            "routes.public_routes, with visual orbit code in web.public_orbit."
        ),
        "next_recommended_steps": [
            "V169: move dashboard HTML into web/dashboard_html.py",
            "V170: move dashboard route helpers into routes/dashboard_routes.py",
            "V171: move public page base builder out of main.py",
        ],
    }
