import base64
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
TOKEN_PATH = PROJECT_ROOT / "token.json"
ENV_PATH = PROJECT_ROOT / ".env"

SCHWAB_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"


def read_dotenv(path: Path) -> dict:
    values = {}

    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key:
            values[key] = value

    return values


def get_config_value(name: str, dotenv_values: dict) -> str:
    return str(os.getenv(name) or dotenv_values.get(name) or "").strip()


def load_token() -> dict:
    if not TOKEN_PATH.exists():
        raise FileNotFoundError(f"Missing token file: {TOKEN_PATH}")

    return json.loads(TOKEN_PATH.read_text(encoding="utf-8"))


def save_token(token_data: dict) -> None:
    token_data["saved_at"] = datetime.now().replace(microsecond=0).isoformat()
    TOKEN_PATH.write_text(json.dumps(token_data, indent=2), encoding="utf-8")


def refresh_token():
    dotenv_values = read_dotenv(ENV_PATH)

    client_id = get_config_value("SCHWAB_CLIENT_ID", dotenv_values)
    client_secret = get_config_value("SCHWAB_CLIENT_SECRET", dotenv_values)

    if not client_id:
        raise RuntimeError("SCHWAB_CLIENT_ID is missing from environment/.env.")

    if not client_secret:
        raise RuntimeError("SCHWAB_CLIENT_SECRET is missing from environment/.env.")

    old_token = load_token()
    refresh_token_value = str(old_token.get("refresh_token") or "").strip()

    if not refresh_token_value:
        raise RuntimeError("token.json has no refresh_token. You need fresh Schwab login.")

    form = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token_value,
    }).encode("utf-8")

    basic_raw = f"{client_id}:{client_secret}".encode("utf-8")
    basic_header = base64.b64encode(basic_raw).decode("ascii")

    req = urllib.request.Request(
        SCHWAB_TOKEN_URL,
        data=form,
        method="POST",
        headers={
            "Authorization": f"Basic {basic_header}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8", errors="replace")
            status_code = response.status
    except Exception as exc:
        raise RuntimeError(f"Refresh request failed: {type(exc).__name__}: {exc}") from exc

    try:
        new_token = json.loads(body)
    except Exception as exc:
        raise RuntimeError(f"Refresh response was not JSON: {body[:1000]}") from exc

    if status_code < 200 or status_code >= 300:
        raise RuntimeError(f"Refresh returned HTTP {status_code}: {body[:1000]}")

    if not isinstance(new_token, dict) or not new_token.get("access_token"):
        raise RuntimeError(f"Refresh response did not contain access_token: {new_token}")

    # Schwab may not always return a new refresh token. Keep the old one if missing.
    if not new_token.get("refresh_token"):
        new_token["refresh_token"] = refresh_token_value

    save_token(new_token)

    return {
        "status": "success",
        "message": "Schwab access token refreshed and token.json was updated.",
        "token_path": str(TOKEN_PATH),
        "saved_at": new_token.get("saved_at"),
        "expires_in": new_token.get("expires_in"),
        "has_access_token": bool(new_token.get("access_token")),
        "has_refresh_token": bool(new_token.get("refresh_token")),
    }


def main():
    print()
    print("============================================================")
    print("Standalone Schwab Token Refresh")
    print("============================================================")
    print()

    result = refresh_token()

    print(json.dumps(result, indent=2))
    print()
    print("Next:")
    print("python .\\download_intraday_test_universe_5m_v1.py")
    print()


if __name__ == "__main__":
    main()
