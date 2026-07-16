from pathlib import Path

path = Path("alientai_v2/v2_routes.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/v2_routes_BACKUP_BEFORE_OPTIONS_ACCOUNT_ENDPOINT.py")
backup.write_text(text, encoding="utf-8")

# Make sure json and Path imports exist.
if "import json" not in text:
    text = "import json\n" + text

if "from pathlib import Path" not in text:
    text = "from pathlib import Path\n" + text

helper = r'''

def _read_v2_options_paper_account_file():
    """
    Directly read the separate V2 options paper account file.
    This endpoint is used by the owner monitor.
    """
    try:
        project_root = Path(__file__).resolve().parents[1]
        account_path = project_root / "data_v2" / "v2_options_paper_account.json"

        if account_path.exists():
            account = json.loads(account_path.read_text(encoding="utf-8-sig"))
            if isinstance(account, dict):
                return {
                    "status": "success",
                    "source": str(account_path),
                    "account": account,
                }

        return {
            "status": "missing",
            "source": str(account_path),
            "account": {
                "starting_balance": 1000.0,
                "cash": 1000.0,
                "open_option_positions": {},
                "closed_option_trades": [],
                "actions": [],
                "open_option_value": 0.0,
                "unrealized_pnl": 0.0,
                "account_value": 1000.0,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "note": "Separate options paper account. This does not place real trades.",
            },
        }

    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "account": {},
        }
'''

if "_read_v2_options_paper_account_file" not in text:
    marker = "@router.get(\"/status\")"
    idx = text.find(marker)
    if idx == -1:
        raise SystemExit("Could not find status route marker.")
    text = text[:idx] + helper + "\n\n" + text[idx:]

route = r'''

@router.get("/options-paper-account")
def v2_options_paper_account():
    return _read_v2_options_paper_account_file()
'''

if '@router.get("/options-paper-account")' not in text:
    # Put this before the monitor route.
    marker = '@router.get("/monitor"'
    idx = text.find(marker)
    if idx == -1:
        text = text.rstrip() + "\n" + route + "\n"
    else:
        text = text[:idx] + route + "\n\n" + text[idx:]

path.write_text(text, encoding="utf-8")
print("Added /v2/options-paper-account endpoint.")
