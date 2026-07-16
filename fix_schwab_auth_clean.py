import os
import json
import secrets
import urllib.parse
from pathlib import Path
from datetime import datetime

try:
    import requests
except Exception:
    raise SystemExit("Missing requests. Run: pip install requests")

try:
    from dotenv import load_dotenv
except Exception:
    raise SystemExit("Missing python-dotenv. Run: pip install python-dotenv")

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
backup_path = PROJECT_ROOT / "old_system_reference" / "token_BACKUP_BEFORE_CLEAN_AUTH_FIX.json"

if not api_key:
    raise SystemExit("Missing SCHWAB_CLIENT_ID / SCHWAB_API_KEY in .env")

if not app_secret:
    raise SystemExit("Missing SCHWAB_CLIENT_SECRET / SCHWAB_APP_SECRET in .env")

state = "ALIENTAI_" + secrets.token_urlsafe(12)

authorize_params = {
    "response_type": "code",
    "client_id": api_key.strip(),
    "redirect_uri": callback_url.strip(),
    "state": state,
}

authorize_url = "https://api.schwabapi.com/v1/oauth/authorize?" + urllib.parse.urlencode(authorize_params)

print("")
print("=" * 80)
print("ALIENTAI CLEAN SCHWAB AUTH FIX")
print("=" * 80)
print("")
print("Using callback URL:")
print(callback_url)
print("")
print("1. Open this URL in an Incognito / Private browser window:")
print("")
print(authorize_url)
print("")
print("2. Log in to Schwab.")
print("3. Click Allow.")
print("4. Copy the ENTIRE final browser address bar.")
print("5. It must contain ?code= and state=" + state)
print("")
print("Example good callback:")
print("https://schwab.alientai.com/auth/callback?code=LONG_CODE&session=...&state=" + state)
print("")

received_url = input("Paste full Schwab callback URL here: ").strip()

if "?code=" not in received_url and "&code=" not in received_url:
    raise SystemExit("BAD URL: callback URL does not contain code=. Start again and copy the full browser address bar.")

parsed = urllib.parse.urlparse(received_url)
query = urllib.parse.parse_qs(parsed.query)

code = (query.get("code") or [""])[0]
returned_state = (query.get("state") or [""])[0]
error = (query.get("error") or [""])[0]
error_description = (query.get("error_description") or [""])[0]

if error:
    raise SystemExit(f"Schwab returned error={error} description={error_description}")

if not code:
    raise SystemExit("No code= value found in callback URL.")

if returned_state != state:
    print("")
    print("WARNING: Returned state does not match this run.")
    print("Expected:", state)
    print("Returned:", returned_state)
    print("This often means an old browser tab or old auth URL was used.")
    raise SystemExit("Use the fresh authorize URL from this run only.")

print("")
print("Authorization code received.")
print("Code length:", len(code))
print("Code preview:", code[:10] + "..." + code[-6:])
print("State OK:", returned_state)

token_url = "https://api.schwabapi.com/v1/oauth/token"

data = {
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": callback_url.strip(),
}

headers = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "AlientAI-OAuth-Fix/1.0",
}

print("")
print("Requesting token from Schwab...")

response = requests.post(
    token_url,
    data=data,
    headers=headers,
    auth=(api_key.strip(), app_secret.strip()),
    timeout=60,
)

print("HTTP status:", response.status_code)
print("Content-Type:", response.headers.get("content-type", ""))

try:
    body = response.json()
except Exception:
    body = {"raw_text": response.text}

if response.status_code != 200:
    print("")
    print("SCHWAB TOKEN EXCHANGE FAILED")
    print(json.dumps(body, indent=2))
    print("")
    print("Meaning:")
    print("invalid_client = client secret/key mismatch in Schwab Developer or .env")
    print("invalid_grant = code expired, code reused, callback mismatch, or wrong app")
    print("invalid_request = request formatting or redirect URI issue")
    raise SystemExit(1)

if not body.get("access_token"):
    print(json.dumps(body, indent=2))
    raise SystemExit("No access_token returned.")

if token_path.exists():
    backup_path.write_text(token_path.read_text(encoding="utf-8"), encoding="utf-8")
    print("Backed up old token to:", backup_path)

body["created_at"] = datetime.now().isoformat(timespec="seconds")
token_path.parent.mkdir(parents=True, exist_ok=True)
token_path.write_text(json.dumps(body, indent=2), encoding="utf-8")

print("")
print("SUCCESS: Schwab token saved.")
print("Token path:", token_path)
print("Access token present:", bool(body.get("access_token")))
print("Refresh token present:", bool(body.get("refresh_token")))
print("Expires in:", body.get("expires_in"))

print("")
print("Testing DIA quote with new token...")

quote_headers = {
    "Authorization": "Bearer " + body["access_token"],
    "Accept": "application/json",
}

quote_response = requests.get(
    "https://api.schwabapi.com/marketdata/v1/quotes",
    params={"symbols": "DIA"},
    headers=quote_headers,
    timeout=60,
)

print("Quote test HTTP status:", quote_response.status_code)

if quote_response.status_code == 200:
    print("QUOTE TEST SUCCESS")
    print("Schwab auth is fixed.")
else:
    print("QUOTE TEST FAILED")
    try:
        print(json.dumps(quote_response.json(), indent=2)[:2000])
    except Exception:
        print(quote_response.text[:2000])
    raise SystemExit(1)
