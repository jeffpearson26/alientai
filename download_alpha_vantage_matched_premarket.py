from __future__ import annotations

"""Archive monthly five-minute extended-hours candles for matched research events."""

import argparse
import gzip
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def event_requests(rows: Iterable[Dict[str, Any]], role: str = "all") -> List[Tuple[str, str]]:
    """Deduplicate requests because one monthly response serves many event dates."""
    output = set()
    for row in rows:
        if role != "all" and str(row.get("study_role") or "") != role:
            continue
        symbol = str(row.get("symbol") or "").strip().upper()
        for field in ("market_date", "future_market_date"):
            day = str(row.get(field) or "").strip()
            if symbol and len(day) >= 7:
                try:
                    month = datetime.strptime(day[:10], "%Y-%m-%d").strftime("%Y-%m")
                except ValueError:
                    continue
                output.add((symbol, month))
    return sorted(output, key=lambda item: (item[1], item[0]))


def safe_error(value: Any, api_key: str) -> str:
    message = str(value or "Alpha Vantage intraday request failed")
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


def archive_path(output: Path, symbol: str, month: str) -> Path:
    safe_symbol = "".join(character for character in symbol if character.isalnum() or character in ".-")
    return output / month[:4] / month / f"{safe_symbol}.csv.gz"


def fetch_month(symbol: str, month: str, api_key: str) -> bytes:
    response = requests.get(
        "https://www.alphavantage.co/query",
        params={
            "function": "TIME_SERIES_INTRADAY", "symbol": symbol, "interval": "5min",
            "month": month, "outputsize": "full", "adjusted": "false",
            "extended_hours": "true", "datatype": "csv", "apikey": api_key,
        },
        timeout=120,
    )
    response.raise_for_status()
    content = response.content
    if not content.strip():
        raise ValueError("Alpha Vantage response lacks intraday data")
    if content.lstrip().startswith(b"{"):
        payload = response.json()
        message = payload.get("Error Message") or payload.get("Note") or payload.get("Information")
        if message:
            raise RuntimeError(message)
    header = content.splitlines()[0].decode("utf-8-sig", errors="replace").casefold()
    if not all(field in header for field in ("timestamp", "open", "high", "low", "close", "volume")):
        raise ValueError("Alpha Vantage response lacks intraday data")
    return content


def write_gzip(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wb", compresslevel=6) as handle:
        handle.write(content)
    replace_with_retry(temporary, path)


def run(items: Iterable[Tuple[str, str]], api_key: str, output: Path, delay: float = 0.75) -> Dict[str, Any]:
    manifest_path = output / "manifest.json"
    manifest = {"status": "running", "completed": [], "unavailable": [], "failed": []}
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        for field in ("completed", "unavailable"):
            manifest[field] = list(dict.fromkeys(previous.get(field, [])))
    completed, unavailable = set(manifest["completed"]), set(manifest["unavailable"])
    for symbol, month in items:
        request_id = f"{symbol}|{month}"
        destination = archive_path(output, symbol, month)
        if request_id in completed or request_id in unavailable or destination.exists():
            continue
        try:
            content = fetch_month(symbol, month, api_key)
            write_gzip(destination, content)
            manifest["completed"].append(request_id)
            completed.add(request_id)
            print(f"DONE {request_id}: {len(content)} bytes", flush=True)
        except ValueError as exc:
            if "lacks intraday data" not in str(exc):
                raise
            manifest["unavailable"].append(request_id)
            unavailable.add(request_id)
            print(f"UNAVAILABLE {request_id}", flush=True)
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
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--role", choices=("winner", "control", "all"), default="all")
    parser.add_argument("--limit-requests", type=int, default=0)
    parser.add_argument("--delay-seconds", type=float, default=0.75)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    items = event_requests(read_jsonl(args.events), args.role)
    if args.limit_requests:
        items = items[: args.limit_requests]
    result = run(items, api_key, args.output, args.delay_seconds)
    print(json.dumps({
        "status": result["status"], "requests": len(items),
        "completed": len(result["completed"]), "unavailable": len(result["unavailable"]),
    }, indent=2))


if __name__ == "__main__":
    main()
