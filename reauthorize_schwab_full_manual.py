import os
from pathlib import Path
from dotenv import load_dotenv

try:
    from schwab.auth import client_from_manual_flow
except Exception as exc:
    raise SystemExit("Missing schwab-py. Run: pip install schwab-py") from exc

PROJECT_ROOT = Path.cwd()
load_dotenv(PROJECT_ROOT / ".env")

# Try several common env names so this works with your existing .env.
api_key = (
    os.getenv("SCHWAB_API_KEY")
    or os.getenv("SCHWAB_APP_KEY")
    or os.getenv("SCHWAB_CLIENT_ID")
    or os.getenv("SCHWAB_CONSUMER_KEY")
    or os.getenv("CHARLES_SCHWAB_API_KEY")
)

app_secret = (
    os.getenv("SCHWAB_APP_SECRET")
    or os.getenv("SCHWAB_CLIENT_SECRET")
    or os.getenv("SCHWAB_SECRET")
    or os.getenv("CHARLES_SCHWAB_APP_SECRET")
)

callback_url = (
    os.getenv("SCHWAB_CALLBACK_URL")
    or os.getenv("SCHWAB_REDIRECT_URI")
    or os.getenv("SCHWAB_REDIRECT_URL")
    or "https://127.0.0.1:8182"
)

token_path = PROJECT_ROOT / "old_system_reference" / "token.json"
backup_path = PROJECT_ROOT / "old_system_reference" / "token_BACKUP_BEFORE_FULL_REAUTH.json"

if not api_key:
    raise SystemExit("Missing Schwab API key in .env. Look for SCHWAB_API_KEY / SCHWAB_APP_KEY / SCHWAB_CLIENT_ID.")
if not app_secret:
    raise SystemExit("Missing Schwab app secret in .env. Look for SCHWAB_APP_SECRET / SCHWAB_CLIENT_SECRET.")
if token_path.exists():
    backup_path.write_text(token_path.read_text(encoding="utf-8"), encoding="utf-8")
    print("Backed up old token to:", backup_path)

print("")
print("Starting Schwab manual OAuth login.")
print("Token will be written to:", token_path)
print("Callback URL being used:", callback_url)
print("")
print("IMPORTANT: The callback URL must exactly match the callback URL in your Schwab developer app.")
print("Follow the instructions printed by schwab-py.")
print("")

client = client_from_manual_flow(
    api_key=api_key,
    app_secret=app_secret,
    callback_url=callback_url,
    token_path=str(token_path),
    enforce_enums=False,
)

print("")
print("Schwab authorization complete.")
print("New token saved to:", token_path)
