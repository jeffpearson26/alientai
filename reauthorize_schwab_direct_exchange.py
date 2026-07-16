import os
import json
import base64
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

PROJECT_ROOT = Path.cwd()
load_dotenv(PROJECT_ROOT / ".env")

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
    or "https://schwab.alientai.com/auth/callback"
)

token_path = PROJECT_ROOT / "old_system_reference" / "token.json"
backup_path = PROJECT_ROOT / "old_system_reference" / "token_BACKUP_BEFORE_DIRECT_EXCHANGE.json"

if not api_key:
    raise SystemExit("Missing Schwab API key/client id in .env")

if not app_secret:
    raise SystemExit("Missing Schwab app secret/client secret in .env")

state = "ALIENTAI_DIRECT_AUTH"

params = {
    "response_type": "code",
    "client_id": api_key,
    "redirect_uri": callback_url,
    "state": state,
}

authorize_url = "https://api.schwabapi.com/v1/oauth/authorize?" + urllib.parse.urlencode(params)

print("")
print("=" * 80)
print("DIRECT SCHWAB AUTHORIZATION")
print("=" * 80)
print("")
print("1. Open this URL in an Incognito/Private browser window:")
print("")
print(authorize_url)
print("")
print("2. Log in to Schwab and click Allow.")
print("3. You may see {'detail':'Not Found'} on the callback page. That is okay.")
print("4. Copy the ENTIRE browser address bar.")
print("5. It MUST contain ?code=...")
print("")

received_url = input("Paste full redirect URL here: ").strip()

if "?code=" not in received_url and "&code=" not in received_url:
    raise SystemExit("The redirect URL does not contain code=. Do not paste only the callback URL.")

parsed = urllib.parse.urlparse(received_url)
query = urllib.parse.parse_qs(parsed.query)

code_values = query.get("code")
state_values = query.get("state")

if not code_values:
    raise SystemExit("Could not find code= in redirect URL.")

code = code_values[0]

print("")
print("Received authorization code.")
print("Code length:", len(code))
print("Code ends with:", code[-5:])
print("Redirect URI used:", callback_url)
print("State returned:", state_values[0] if state_values else "")

# Schwab authorization codes often end in %40 in the browser URL.
# urllib.parse.parse_qs decodes that to @, which is what the token endpoint expects.
if "%40" in code:
    print("WARNING: code still contains %40. Decoding it.")
    code = code.replace("%40", "@")

basic = base64.b64encode(f"{api_key}:{app_secret}".encode("utf-8")).decode("ascii")

body = urllib.parse.urlencode({
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": callback_url,
}).encode("utf-8")

req = urllib.request.Request(
    "https://api.schwabapi.com/v1/oauth/token",
    data=body,
    method="POST",
    headers={
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    },
)

print("")
print("Requesting token directly from Schwab...")

try:
    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read().decode("utf-8")
        token = json.loads(raw)
except urllib.error.HTTPError as exc:
    error_body = exc.read().decode("utf-8", errors="replace")
    print("")
    print("SCHWAB TOKEN EXCHANGE FAILED")
    print("HTTP status:", exc.code)
    print("Response body:")
    print(error_body)
    raise SystemExit(1)

if token_path.exists():
    backup_path.write_text(token_path.read_text(encoding="utf-8"), encoding="utf-8")
    print("Backed up old token to:", backup_path)

token["created_at"] = datetime.now().isoformat(timespec="seconds")
token_path.write_text(json.dumps(token, indent=2), encoding="utf-8")

print("")
print("SUCCESS")
print("New Schwab token saved to:", token_path)
print("access_token present:", bool(token.get("access_token")))
print("refresh_token present:", bool(token.get("refresh_token")))
print("expires_in:", token.get("expires_in"))
