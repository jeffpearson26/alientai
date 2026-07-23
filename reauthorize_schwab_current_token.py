from __future__ import annotations

"""Interactive one-time Schwab reauthorization for AlienTAI's current token file."""

import base64
import json
import os
import secrets
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
TOKEN_PATH = ROOT / "token.json"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
AUTHORIZE_URL = "https://api.schwabapi.com/v1/oauth/authorize"


def setting(values: Mapping[str, str], *names: str) -> str:
    for name in names:
        value = str(os.getenv(name) or values.get(name) or "").strip()
        if value:
            return value
    return ""


def authorization_url(client_id: str, redirect_uri: str, state: str) -> str:
    return AUTHORIZE_URL + "?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": client_id,
        "redirect_uri": redirect_uri, "state": state,
    })


def redirect_code(redirect_url: str, expected_state: str) -> str:
    parsed = urllib.parse.urlparse(redirect_url.strip())
    query = urllib.parse.parse_qs(parsed.query)
    if query.get("state", [""])[0] != expected_state:
        raise ValueError("callback state did not match this authorization attempt")
    error = query.get("error", [""])[0]
    if error:
        raise ValueError(f"Schwab authorization returned {error}")
    code = query.get("code", [""])[0]
    if not code:
        raise ValueError("callback URL did not contain an authorization code")
    return code


def exchange_code(client_id: str, client_secret: str, redirect_uri: str, code: str) -> dict:
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
    }).encode("utf-8")
    request = urllib.request.Request(TOKEN_URL, data=body, method="POST", headers={
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Schwab token exchange failed ({type(exc).__name__}); no token was changed.") from None
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise RuntimeError("Schwab token exchange returned no access token; no token was changed.")
    return payload


def save_token(token: dict) -> None:
    token = {**token, "saved_at": datetime.now().isoformat(timespec="seconds")}
    temporary = TOKEN_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(token, indent=2) + "\n", encoding="utf-8")
    temporary.replace(TOKEN_PATH)


def main() -> None:
    load_dotenv(ROOT / ".env")
    values = {name: str(os.getenv(name) or "") for name in os.environ}
    client_id = setting(values, "SCHWAB_CLIENT_ID", "SCHWAB_API_KEY", "SCHWAB_APP_KEY")
    client_secret = setting(values, "SCHWAB_CLIENT_SECRET", "SCHWAB_APP_SECRET")
    redirect_uri = setting(values, "SCHWAB_CALLBACK_URL", "SCHWAB_REDIRECT_URI", "SCHWAB_REDIRECT_URL")
    if not all((client_id, client_secret, redirect_uri)):
        raise RuntimeError("Missing Schwab client ID, client secret, or registered callback URL in .env.")
    state = "alientai_" + secrets.token_urlsafe(18)
    print("Open this URL in your browser, sign in to Schwab, approve access, then paste the complete callback URL here:")
    print(authorization_url(client_id, redirect_uri, state))
    callback = input("Callback URL: ")
    token = exchange_code(client_id, client_secret, redirect_uri, redirect_code(callback, state))
    save_token(token)
    print(json.dumps({"status": "success", "token_path": str(TOKEN_PATH), "has_access_token": True, "has_refresh_token": bool(token.get("refresh_token"))}, indent=2))


if __name__ == "__main__":
    main()
