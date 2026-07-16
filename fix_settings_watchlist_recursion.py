from pathlib import Path

path = Path("alientai_v2/settings.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/settings_BACKUP_FIX_WATCHLIST_RECURSION.py")
backup.write_text(text, encoding="utf-8")

old = '''def apply_live_watchlist_priority(settings: dict) -> dict:
    """
    Force the live file watchlist to override default/settings watchlists.
    """
    if not isinstance(settings, dict):
        settings = {}

    file_symbols = load_watchlist_file_symbols()

    if file_symbols:
        settings["watchlist"] = file_symbols
        settings["symbols"] = file_symbols
        settings["v2_watchlist"] = file_symbols
        settings["v2_live_watchlist"] = file_symbols
        settings["live_watchlist"] = file_symbols
        settings["watchlist_source"] = "v2_live_watchlist_symbols.txt"
        settings["watchlist_count"] = len(file_symbols)

    return apply_live_watchlist_priority(settings)
'''

new = '''def apply_live_watchlist_priority(settings: dict) -> dict:
    """
    Force the live file watchlist to override default/settings watchlists.
    """
    if not isinstance(settings, dict):
        settings = {}

    file_symbols = load_watchlist_file_symbols()

    if file_symbols:
        settings["watchlist"] = file_symbols
        settings["symbols"] = file_symbols
        settings["v2_watchlist"] = file_symbols
        settings["v2_live_watchlist"] = file_symbols
        settings["live_watchlist"] = file_symbols
        settings["watchlist_source"] = "v2_live_watchlist_symbols.txt"
        settings["watchlist_count"] = len(file_symbols)

    return settings
'''

if old not in text:
    # Smaller fallback fix in case spacing differs.
    text = text.replace(
        "return apply_live_watchlist_priority(settings)",
        "return settings",
        1 if text.count("return apply_live_watchlist_priority(settings)") == 1 else text.count("return apply_live_watchlist_priority(settings)") - 1
    )
else:
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("Fixed recursive apply_live_watchlist_priority return.")
