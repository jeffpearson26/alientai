from pathlib import Path

path = Path("alientai_v2/engine.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/engine_BACKUP_BEFORE_OPTIONS_PAPER_BUY.py")
backup.write_text(text, encoding="utf-8")

if "from alientai_v2.options_paper import maybe_buy_from_research_rows" not in text:
    import_anchor = "from alientai_v2.settings import load_settings"
    text = text.replace(
        import_anchor,
        import_anchor + "\nfrom alientai_v2.options_paper import maybe_buy_from_research_rows",
        1,
    )

if '"options_paper_manager"' not in text:
    old = '''    scored = run_enabled_engines(quotes, settings)
'''
    new = '''    scored = run_enabled_engines(quotes, settings)

    options_paper_result = {}
    try:
        option_rows = [
            row for row in scored
            if isinstance(row, dict) and str(row.get("engine_id")) == "options_research"
        ]
        options_paper_result = maybe_buy_from_research_rows(option_rows, settings)
    except Exception as exc:
        options_paper_result = {
            "status": "error",
            "message": f"Options paper manager error: {exc}",
            "actions": [],
        }
'''
    if old not in text:
        raise SystemExit("Could not find scored = run_enabled_engines(quotes, settings).")
    text = text.replace(old, new, 1)

    # Add result into save_status payload near candidate fields.
    old_payload_piece = '''        "top_v2_candidates": scored[:80],
'''
    new_payload_piece = '''        "top_v2_candidates": scored[:80],
        "options_paper_manager": options_paper_result,
        "options_paper_account": options_paper_result.get("account") if isinstance(options_paper_result, dict) else {},
        "options_paper_actions": options_paper_result.get("actions", []) if isinstance(options_paper_result, dict) else [],
'''
    if old_payload_piece in text:
        text = text.replace(old_payload_piece, new_payload_piece, 1)
    else:
        print("Could not find top_v2_candidates payload line. Options manager will still run, but status may not expose account.")

path.write_text(text, encoding="utf-8")
print("Patched engine.py for options paper buying.")
