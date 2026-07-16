from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"


def load_env_file(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and value:
            os.environ[key] = value


def env_value(*names: str) -> Optional[str]:
    load_env_file()

    for name in names:
        value = os.environ.get(name)
        if value:
            return value

    return None


def supabase_headers() -> Dict[str, str]:
    key = env_value("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_PUBLISHABLE_KEY")

    if not key:
        raise RuntimeError("Supabase key missing. Expected SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SERVICE_KEY.")

    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }


def supabase_url() -> str:
    url = env_value("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")

    if not url:
        raise RuntimeError("SUPABASE_URL missing from .env.")

    return url.rstrip("/")


def fetch_symbol_candles(
    symbol: str,
    *,
    table: str = "v2_5min_candles",
    limit: int = 5000,
    before_ms: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetches recent historical 5-minute candles for one symbol from Supabase.

    We order descending in the request for speed, then reverse to chronological order.
    """

    symbol = str(symbol or "").upper().strip()

    if not symbol:
        return []

    base_url = supabase_url()
    url = f"{base_url}/rest/v1/{table}"

    params: Dict[str, str] = {
        "select": "symbol,datetime_ms,datetime_utc,open,high,low,close,volume",
        "symbol": f"eq.{symbol}",
        "order": "datetime_ms.desc",
        "limit": str(int(limit)),
    }

    if before_ms:
        params["datetime_ms"] = f"lt.{int(before_ms)}"

    response = requests.get(
        url,
        headers=supabase_headers(),
        params=params,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Supabase candle fetch failed HTTP {response.status_code}: {response.text[:500]}")

    rows = response.json()

    if not isinstance(rows, list):
        return []

    rows.reverse()
    return rows


def fetch_symbols_available(
    *,
    table: str = "v2_5min_candles",
    limit: int = 1000,
) -> List[str]:
    """
    Lightweight helper. Uses a grouped RPC only if available would be better,
    but plain REST cannot group easily. This is not used by the live engine.
    """
    base_url = supabase_url()
    url = f"{base_url}/rest/v1/{table}"

    params = {
        "select": "symbol",
        "limit": str(int(limit)),
    }

    response = requests.get(
        url,
        headers=supabase_headers(),
        params=params,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Supabase symbol fetch failed HTTP {response.status_code}: {response.text[:500]}")

    symbols = sorted(set(str(r.get("symbol") or "").upper().strip() for r in response.json() if r.get("symbol")))
    return symbols
