"""Archive isolated Alpha Vantage daily-price fallback data for research review.

This collector deliberately does not update the Schwab archive, Supabase, a
model, or any trading component.  Its outputs remain source-separated so a
future evaluator can require one consistent price source for each outcome.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from dotenv import load_dotenv

from alpha_vantage_http import get_alpha_vantage_response, redact_sensitive_text


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = Path(r"D:\AlientAI\Data\AlphaVantage_2026\prospective_daily_research_fallback")


def payload_symbols(payload: Mapping[str, Any]) -> list[str]:
    """Return deduplicated payload symbols, rejecting any execution-capable input."""
    if payload.get("execution_enabled") is not False or not payload.get("research_only"):
        raise ValueError("payload must be explicitly research-only and execution-disabled")
    symbols = [str(item.get("symbol") or "").strip().upper() for item in payload.get("candidates") or []]
    return list(dict.fromkeys(symbol for symbol in symbols if symbol))


def fetch_daily(symbol: str, api_key: str) -> bytes:
    response = get_alpha_vantage_response(
        {"function": "TIME_SERIES_DAILY", "symbol": symbol, "outputsize": "compact"},
        api_key,
        timeout=90,
    )
    content = response.content
    try:
        parsed = response.json()
    except ValueError as exc:
        raise RuntimeError("Alpha Vantage daily response was not JSON") from exc
    if not isinstance(parsed, Mapping) or not any(str(key).startswith("Time Series") for key in parsed):
        message = parsed.get("Error Message") or parsed.get("Note") or parsed.get("Information") if isinstance(parsed, Mapping) else ""
        raise RuntimeError(str(message or "Alpha Vantage daily response had no time series"))
    return content


def write_gzip(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wb", compresslevel=6) as handle:
        handle.write(content)
    temporary.replace(path)


def collect(symbols: Iterable[str], output: Path, api_key: str, fetcher: Callable[[str, str], bytes] = fetch_daily) -> dict[str, Any]:
    collected_at = datetime.now(timezone.utc)
    destination = output / collected_at.date().isoformat()
    files = []
    for symbol in symbols:
        content = fetcher(symbol, api_key)
        path = destination / f"{symbol}_daily.json.gz"
        write_gzip(path, content)
        files.append({"symbol": symbol, "path": str(path), "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)})
    result = {
        "status": "complete", "research_only": True, "execution_enabled": False,
        "source": "alpha_vantage_time_series_daily", "collected_at_utc": collected_at.isoformat(),
        "files": files,
        "warning": "Separate archival fallback only. Do not mix this source into Schwab outcomes or model inputs.",
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive source-separated Alpha Vantage daily research fallback data.")
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    try:
        result = collect(payload_symbols(json.loads(args.payload.read_text(encoding="utf-8"))), args.output, api_key)
    except Exception as exc:
        raise RuntimeError(redact_sensitive_text(exc, api_key)) from None
    print(json.dumps({"status": result["status"], "files": len(result["files"]), "source": result["source"]}, indent=2))


if __name__ == "__main__":
    main()
