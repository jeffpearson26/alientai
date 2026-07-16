from pathlib import Path

path = Path("main.py")
text = path.read_text(encoding="utf-8-sig")

marker = "# --- ALIENTAI PUBLIC V2 PAGE WIRING ---"

patch = r'''
# --- ALIENTAI PUBLIC V2 PAGE WIRING ---
# Public page is read-only and connected to clean V2 status.
try:
    from alientai_v2.public_v2_page import public_v2_page

    # Remove older /public route if it already exists.
    app.router.routes = [
        route for route in app.router.routes
        if getattr(route, "path", None) not in {"/public"}
    ]

    app.add_api_route(
        "/public",
        public_v2_page,
        methods=["GET"],
        include_in_schema=False,
    )

    app.add_api_route(
        "/public-v2",
        public_v2_page,
        methods=["GET"],
        include_in_schema=False,
    )

except Exception as exc:
    print(f"Public V2 page wiring failed: {exc}")
# --- END ALIENTAI PUBLIC V2 PAGE WIRING ---
'''

if marker not in text:
    text = text.rstrip() + "\n\n" + patch + "\n"

path.write_text(text, encoding="utf-8")
