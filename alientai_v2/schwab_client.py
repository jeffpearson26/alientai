from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from alientai_v2.utils import PROJECT_ROOT, safe_float


_old_main_module = None


def _load_env_file(path: Path) -> None:
    """
    Load KEY=VALUE lines from a .env file into os.environ.
    This forces Schwab credentials to be visible before old quote code runs.
    """

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


def _prepare_schwab_environment() -> None:
    """
    Prepare temporary Schwab bridge environment.

    The clean V2 app still temporarily borrows fetch_quotes_chunked()
    from the old reference file. This function makes sure that old code
    can see the same .env and token.json as the clean app.
    """

    root_env = PROJECT_ROOT / ".env"
    old_env = PROJECT_ROOT / "old_system_reference" / ".env"

    _load_env_file(root_env)
    _load_env_file(old_env)

    root_token = PROJECT_ROOT / "token.json"
    old_token = PROJECT_ROOT / "old_system_reference" / "token.json"

    if root_token.exists():
        old_token.parent.mkdir(parents=True, exist_ok=True)
        old_token.write_text(root_token.read_text(encoding="utf-8"), encoding="utf-8")


def _find_old_main_reference() -> Path:
    old_refs = sorted((PROJECT_ROOT / "old_system_reference").glob("main_old_reference_*.py"), reverse=True)
    if old_refs:
        return old_refs[0]

    root_refs = sorted(PROJECT_ROOT.glob("main_OLD_MONSTER_REFERENCE_*.py"), reverse=True)
    if root_refs:
        return root_refs[0]

    raise RuntimeError("No old main reference file found for temporary Schwab quote access.")


def _load_old_main_module():
    global _old_main_module

    if _old_main_module is not None:
        return _old_main_module

    _prepare_schwab_environment()

    path = _find_old_main_reference()

    old_cwd = os.getcwd()

    try:
        # Old code may use relative token/.env paths.
        # Loading it from its own folder makes those relative paths work.
        os.chdir(str(path.parent))

        spec = importlib.util.spec_from_file_location("alientai_old_main_reference", str(path))
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load old main reference from {path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules["alientai_old_main_reference"] = module
        spec.loader.exec_module(module)

        _old_main_module = module
        return module

    finally:
        os.chdir(old_cwd)


def quote_value(raw: Dict[str, Any], *names: str, default: float = 0.0) -> float:
    old = _load_old_main_module()
    old_quote_value = getattr(old, "quote_value", None)

    if callable(old_quote_value):
        return old_quote_value(raw, *names, default=default)

    quote_section = raw.get("quote") if isinstance(raw, dict) else {}
    if not isinstance(quote_section, dict):
        quote_section = {}

    for name in names:
        if name in quote_section and quote_section.get(name) is not None:
            return safe_float(quote_section.get(name), default)

        if isinstance(raw, dict) and name in raw and raw.get(name) is not None:
            return safe_float(raw.get(name), default)

    return default


def fetch_quotes_chunked(symbols: List[str], chunk_size: int = 100) -> Dict[str, Any]:
    _prepare_schwab_environment()

    old = _load_old_main_module()
    fn = getattr(old, "fetch_quotes_chunked", None)

    if not callable(fn):
        raise RuntimeError("Old main reference does not contain fetch_quotes_chunked().")

    return fn(symbols, chunk_size=chunk_size)


def get_real_v2_quotes(symbols: List[str]) -> List[Dict[str, Any]]:
    result = fetch_quotes_chunked(symbols, chunk_size=100)

    if not isinstance(result, dict):
        raise RuntimeError("Schwab quote result was not a dictionary.")

    if result.get("status") not in {"success", "partial_success"}:
        raise RuntimeError(f"Schwab quotes failed: {result}")

    raw_quotes = result.get("quotes", {})

    if not isinstance(raw_quotes, dict):
        raise RuntimeError("Schwab quote payload did not contain a quotes dictionary.")

    cleaned: List[Dict[str, Any]] = []

    for symbol in symbols:
        symbol = str(symbol).upper()
        raw = raw_quotes.get(symbol)

        if not isinstance(raw, dict):
            continue

        price = quote_value(raw, "mark", "lastPrice", "regularMarketLastPrice", "closePrice", default=0.0)
        bid = quote_value(raw, "bidPrice", "bid", default=0.0)
        ask = quote_value(raw, "askPrice", "ask", default=0.0)
        close = quote_value(raw, "closePrice", "regularMarketPreviousClose", default=0.0)
        net_pct = quote_value(raw, "netPercentChange", "regularMarketPercentChange", default=0.0)
        volume = quote_value(raw, "totalVolume", "regularMarketTotalVolume", "volume", default=0.0)
        avg_volume = quote_value(raw, "averageVolume", "avg10DaysVolume", "avg1YearVolume", default=0.0)

        relative_volume = 1.0
        if avg_volume and avg_volume > 0:
            relative_volume = volume / avg_volume

        spread_percent = 99.0
        if bid > 0 and ask > 0 and ask >= bid:
            mid = (bid + ask) / 2.0
            if mid > 0:
                spread_percent = ((ask - bid) / mid) * 100.0
        elif price > 0:
            spread_percent = 0.25

        cleaned.append({
            "symbol": symbol,
            "price": round(float(price), 4),
            "net_change_percent": round(float(net_pct), 4),
            "relative_volume": round(float(relative_volume), 4),
            "spread_percent": round(float(spread_percent), 4),
            "volume": float(volume),
            "bid": float(bid),
            "ask": float(ask),
            "close": float(close),
            "source": "schwab_live_quote",
        })

    return cleaned
