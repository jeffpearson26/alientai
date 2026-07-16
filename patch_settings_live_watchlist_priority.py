from pathlib import Path

path = Path("alientai_v2/settings.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/settings_BACKUP_BEFORE_WATCHLIST_FILE_PRIORITY.py")
backup.write_text(text, encoding="utf-8")

# Add/import Path/json if missing.
if "from pathlib import Path" not in text:
    text = "from pathlib import Path\n" + text

if "import json" not in text:
    text = "import json\n" + text

helper = r'''

def load_watchlist_file_symbols() -> list[str]:
    """
    Highest-priority live V2 watchlist loader.

    This intentionally reads v2_live_watchlist_symbols.txt directly so V2 does not
    get stuck on DEFAULT_SETTINGS or an older settings object.
    """
    project_root = Path(__file__).resolve().parents[1]
    watchlist_path = project_root / "v2_live_watchlist_symbols.txt"

    if not watchlist_path.exists():
        return []

    try:
        symbols = [
            x.strip().upper()
            for x in watchlist_path.read_text(encoding="utf-8-sig").splitlines()
            if x.strip() and not x.strip().startswith("#")
        ]
        return list(dict.fromkeys(symbols))
    except Exception:
        return []


def apply_live_watchlist_priority(settings: dict) -> dict:
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

if "def load_watchlist_file_symbols" not in text:
    text = text.rstrip() + "\n" + helper + "\n"

# Make load_settings apply live watchlist priority before returning.
if "def load_settings" not in text:
    raise SystemExit("Could not find def load_settings in alientai_v2/settings.py")

# Patch every simple return settings in load_settings-style file.
# This is safe: applying watchlist priority to settings is what we want.
text = text.replace("return settings", "return apply_live_watchlist_priority(settings)")

# If the function returns DEFAULT_SETTINGS directly anywhere, patch that too.
text = text.replace("return DEFAULT_SETTINGS", "return apply_live_watchlist_priority(dict(DEFAULT_SETTINGS))")

path.write_text(text, encoding="utf-8")
print("Patched settings.py so v2_live_watchlist_symbols.txt has priority.")
