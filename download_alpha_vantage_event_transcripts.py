from __future__ import annotations

"""Collect latest safely available earnings-call transcript for research events."""

import argparse
import gzip
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterable, List, Tuple

from dotenv import load_dotenv

from alpha_vantage_http import get_alpha_vantage_response, redact_sensitive_text


ROOT = Path(__file__).resolve().parent


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def fiscal_quarter(fiscal_date: str) -> str:
    day = datetime.fromisoformat(fiscal_date).date()
    return f"{day.year}Q{((day.month - 1) // 3) + 1}"


def transcript_requests(
    research_rows: Iterable[Dict[str, Any]], earnings_rows: Iterable[Dict[str, Any]],
    role: str = "winner", availability_buffer_days: int = 1,
) -> List[Tuple[str, str]]:
    earnings_by_ticker: DefaultDict[str, List[Tuple[datetime, str]]] = defaultdict(list)
    for row in earnings_rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        available = str(row.get("available_at_utc") or "").strip()
        fiscal = str(row.get("fiscal_date_ending") or "").strip()
        if ticker and available and fiscal and fiscal[:4].isdigit() and int(fiscal[:4]) >= 2010:
            earnings_by_ticker[ticker].append((utc(available), fiscal_quarter(fiscal)))
    for values in earnings_by_ticker.values():
        values.sort()
    output = set()
    buffer = timedelta(days=availability_buffer_days)
    for row in research_rows:
        if role != "all" and str(row.get("study_role") or "") != role:
            continue
        ticker = str(row.get("symbol") or "").strip().upper()
        as_of = str(row.get("as_of_utc") or "").strip()
        if not ticker or not as_of:
            continue
        cutoff = utc(as_of) - buffer
        eligible = [quarter for available, quarter in earnings_by_ticker.get(ticker, []) if available <= cutoff]
        if eligible:
            output.add((ticker, eligible[-1]))
    return sorted(output)


def safe_error(value: Any, api_key: str) -> str:
    return redact_sensitive_text(value or "Alpha Vantage transcript request failed", api_key)


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


def fetch_transcript(symbol: str, quarter: str, api_key: str) -> Dict[str, Any]:
    response = get_alpha_vantage_response(
        {"function": "EARNINGS_CALL_TRANSCRIPT", "symbol": symbol, "quarter": quarter},
        api_key,
        timeout=90,
    )
    payload = response.json()
    message = payload.get("Error Message") or payload.get("Note") or payload.get("Information")
    if message:
        raise RuntimeError(message)
    if not isinstance(payload.get("transcript"), list) or not payload["transcript"]:
        raise ValueError("Alpha Vantage response lacks transcript")
    return payload


def write_archive(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=6) as handle:
        json.dump(payload, handle, separators=(",", ":"))
    replace_with_retry(temporary, path)


def run(items: Iterable[Tuple[str, str]], api_key: str, output: Path, delay: float = 0.75) -> Dict[str, Any]:
    manifest_path = output / "manifest.json"
    manifest = {"status": "running", "completed": [], "unavailable": [], "failed": []}
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        for field in ("completed", "unavailable"):
            manifest[field] = list(dict.fromkeys(previous.get(field, [])))
    completed, unavailable = set(manifest["completed"]), set(manifest["unavailable"])
    for symbol, quarter in items:
        request_id = f"{symbol}|{quarter}"
        destination = output / quarter[:4] / quarter / f"{symbol}.json.gz"
        if request_id in completed or request_id in unavailable or destination.exists():
            continue
        try:
            payload = fetch_transcript(symbol, quarter, api_key)
            payload["alientai_collected_at_utc"] = datetime.now(timezone.utc).isoformat()
            write_archive(destination, payload)
            manifest["completed"].append(request_id)
            completed.add(request_id)
            print(f"DONE {request_id}: {len(payload['transcript'])} turns")
        except ValueError as exc:
            if "lacks transcript" not in str(exc):
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
    parser.add_argument("--earnings", type=Path, default=ROOT / "data_v2" / "earnings_history" / "earnings_events.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--role", choices=("winner", "control", "all"), default="winner")
    parser.add_argument("--availability-buffer-days", type=int, default=1)
    parser.add_argument("--limit-requests", type=int, default=0)
    parser.add_argument("--delay-seconds", type=float, default=0.75)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    items = transcript_requests(read_jsonl(args.events), read_jsonl(args.earnings), args.role, args.availability_buffer_days)
    if args.limit_requests:
        items = items[:args.limit_requests]
    result = run(items, api_key, args.output, args.delay_seconds)
    print(json.dumps({"status": result["status"], "requests": len(items), "completed": len(result["completed"]), "unavailable": len(result["unavailable"])}, indent=2))


if __name__ == "__main__":
    main()
