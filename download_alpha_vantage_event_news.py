from __future__ import annotations

"""Collect leakage-safe Alpha Vantage news windows around research events."""

import argparse
import gzip
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def event_requests(rows: Iterable[Dict[str, Any]], role: str = "winner") -> List[Tuple[str, datetime]]:
    output = set()
    for row in rows:
        if role != "all" and str(row.get("study_role") or "") != role:
            continue
        symbol = str(row.get("symbol") or "").strip().upper()
        as_of = str(row.get("as_of_utc") or "").strip()
        if symbol and as_of:
            output.add((symbol, parse_utc(as_of)))
    return sorted(output, key=lambda item: (item[1], item[0]))


def av_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M")


def safe_error(value: Any, api_key: str) -> str:
    message = str(value or "Alpha Vantage news request failed")
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


def fetch_news(symbol: str, as_of: datetime, lookback_days: int, api_key: str, limit: int) -> Dict[str, Any]:
    response = requests.get(
        "https://www.alphavantage.co/query",
        params={
            "function": "NEWS_SENTIMENT", "tickers": symbol,
            "time_from": av_time(as_of - timedelta(days=lookback_days)),
            "time_to": av_time(as_of), "sort": "LATEST", "limit": str(limit), "apikey": api_key,
        }, timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    message = payload.get("Error Message") or payload.get("Note") or payload.get("Information")
    if message:
        raise RuntimeError(message)
    if not isinstance(payload.get("feed"), list):
        raise ValueError("Alpha Vantage response lacks news feed")
    return payload


def archive_path(output: Path, symbol: str, as_of: datetime) -> Path:
    stamp = as_of.strftime("%Y%m%dT%H%MZ")
    return output / as_of.strftime("%Y") / as_of.strftime("%Y-%m-%d") / f"{symbol}_{stamp}.json.gz"


def write_archive(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=6) as handle:
        json.dump(payload, handle, separators=(",", ":"))
    replace_with_retry(temporary, path)


def run(items: Iterable[Tuple[str, datetime]], api_key: str, output: Path, lookback_days: int = 14, limit: int = 1000, delay: float = 0.75) -> Dict[str, Any]:
    manifest_path = output / "manifest.json"
    manifest = {"status": "running", "completed": [], "unavailable": [], "failed": []}
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        for field in ("completed", "unavailable"):
            manifest[field] = list(dict.fromkeys(previous.get(field, [])))
    completed, unavailable = set(manifest["completed"]), set(manifest["unavailable"])
    for symbol, as_of in items:
        request_id = f"{symbol}|{as_of.isoformat()}"
        destination = archive_path(output, symbol, as_of)
        if request_id in completed or request_id in unavailable or destination.exists():
            continue
        try:
            payload = fetch_news(symbol, as_of, lookback_days, api_key, limit)
            payload["alientai_request"] = {
                "symbol": symbol, "as_of_utc": as_of.isoformat(), "lookback_days": lookback_days,
            }
            write_archive(destination, payload)
            manifest["completed"].append(request_id)
            completed.add(request_id)
            print(f"DONE {request_id}: {len(payload['feed'])} articles")
        except ValueError as exc:
            if "lacks news feed" not in str(exc):
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
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--role", choices=("winner", "control", "all"), default="winner")
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument("--limit-per-request", type=int, default=1000)
    parser.add_argument("--limit-requests", type=int, default=0)
    parser.add_argument("--delay-seconds", type=float, default=0.75)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    items = event_requests(read_jsonl(args.events), args.role)
    if args.limit_requests:
        items = items[:args.limit_requests]
    result = run(items, api_key, args.output, args.lookback_days, args.limit_per_request, args.delay_seconds)
    print(json.dumps({"status": result["status"], "requests": len(items), "completed": len(result["completed"]), "unavailable": len(result["unavailable"])}, indent=2))


if __name__ == "__main__":
    main()
