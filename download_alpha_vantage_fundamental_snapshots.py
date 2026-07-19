from __future__ import annotations

"""Collect timestamped, compressed Alpha Vantage fundamental snapshots."""

import argparse
import gzip
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
ENDPOINTS = {
    "EARNINGS_ESTIMATES", "SHARES_OUTSTANDING", "INSTITUTIONAL_HOLDINGS",
    "INCOME_STATEMENT", "BALANCE_SHEET", "CASH_FLOW", "OVERVIEW",
}


def read_symbols(path: Path) -> List[str]:
    symbols: List[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        symbol = line.split(",", 1)[0].strip().upper()
        if symbol and not symbol.startswith("#") and symbol not in symbols:
            symbols.append(symbol)
    return symbols


def safe_error(value: Any, api_key: str) -> str:
    message = str(value or "Alpha Vantage request failed")
    return message.replace(api_key, "[REDACTED]")[:1000] if api_key else message[:1000]


def replace_with_retry(source: Path, destination: Path, attempts: int = 8) -> None:
    for attempt in range(attempts):
        try:
            source.replace(destination)
            return
        except PermissionError:
            if attempt + 1 == attempts:
                raise
            time.sleep(0.25 * (attempt + 1))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    replace_with_retry(temporary, path)


def write_snapshot(path: Path, endpoint: str, symbol: str, payload: Dict[str, Any], collected_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    document = {
        "provider": "alpha_vantage", "endpoint": endpoint, "symbol": symbol,
        "collected_at_utc": collected_at, "payload": payload,
    }
    with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=6) as handle:
        json.dump(document, handle, separators=(",", ":"))
    replace_with_retry(temporary, path)


def fetch(endpoint: str, symbol: str, api_key: str) -> Dict[str, Any]:
    response = requests.get(
        "https://www.alphavantage.co/query",
        params={"function": endpoint, "symbol": symbol, "apikey": api_key}, timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    message = payload.get("Error Message") or payload.get("Note") or payload.get("Information")
    if message:
        raise RuntimeError(message)
    if not isinstance(payload, dict) or len(payload) < 2:
        raise ValueError("Alpha Vantage response lacks snapshot data")
    return payload


def run(symbols: Iterable[str], endpoints: Iterable[str], api_key: str, output: Path, delay: float = 0.5) -> Dict[str, Any]:
    manifest_path = output / "manifest.json"
    manifest = {"status": "running", "completed": [], "unavailable": [], "failed": []}
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        for field in ("completed", "unavailable"):
            manifest[field] = list(dict.fromkeys(previous.get(field, [])))
    completed, unavailable = set(manifest["completed"]), set(manifest["unavailable"])
    for endpoint in endpoints:
        if endpoint not in ENDPOINTS:
            raise ValueError(f"unsupported endpoint: {endpoint}")
        for symbol in symbols:
            request_id = f"{endpoint}|{symbol}"
            destination = output / endpoint.lower() / f"{symbol}.json.gz"
            if request_id in completed or request_id in unavailable or destination.exists():
                continue
            collected_at = datetime.now(timezone.utc).isoformat()
            try:
                payload = fetch(endpoint, symbol, api_key)
                write_snapshot(destination, endpoint, symbol, payload, collected_at)
                manifest["completed"].append(request_id)
                completed.add(request_id)
                print(f"DONE {request_id}")
            except ValueError as exc:
                if "lacks snapshot data" not in str(exc):
                    raise
                manifest["unavailable"].append(request_id)
                unavailable.add(request_id)
                print(f"UNAVAILABLE {request_id}")
            except Exception as exc:
                manifest["status"] = "failed_closed"
                manifest["failed"].append({"request": request_id, "error": safe_error(exc, api_key)})
                manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
                atomic_json(manifest_path, manifest)
                raise
            manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_json(manifest_path, manifest)
            if delay:
                time.sleep(delay)
    manifest["status"] = "complete"
    manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    atomic_json(manifest_path, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--endpoints", nargs="+", default=["EARNINGS_ESTIMATES"])
    parser.add_argument("--limit-symbols", type=int, default=0)
    parser.add_argument("--delay-seconds", type=float, default=0.5)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    symbols = read_symbols(args.symbols_file)
    if args.limit_symbols:
        symbols = symbols[:args.limit_symbols]
    result = run(symbols, [item.upper() for item in args.endpoints], api_key, args.output, args.delay_seconds)
    print(json.dumps({"status": result["status"], "completed": len(result["completed"]), "unavailable": len(result["unavailable"])}, indent=2))


if __name__ == "__main__":
    main()
