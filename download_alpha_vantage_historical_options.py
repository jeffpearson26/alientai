from __future__ import annotations

"""Resumable, compressed Alpha Vantage historical-options event collector."""

import argparse
import gzip
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from dotenv import load_dotenv

from alpha_vantage_http import get_alpha_vantage_response, redact_sensitive_text


ROOT = Path(__file__).resolve().parent


def safe_error(value: Any, api_key: str) -> str:
    return redact_sensitive_text(value or "Alpha Vantage request failed", api_key)


def event_requests(
    rows: Iterable[Dict[str, Any]], role: str = "winner", *, include_future_date: bool = True,
    start_date: str = "", end_date: str = "",
) -> List[Tuple[str, str]]:
    requests_to_make = set()
    for row in rows:
        if role != "all" and str(row.get("study_role") or "") != role:
            continue
        symbol = str(row.get("symbol") or "").strip().upper()
        fields = ("market_date", "future_market_date") if include_future_date else ("market_date",)
        for field in fields:
            day = str(row.get(field) or "").strip()
            if symbol and len(day) == 10 and (not start_date or day >= start_date) and (not end_date or day <= end_date):
                requests_to_make.add((symbol, day))
    return sorted(requests_to_make, key=lambda item: (item[1], item[0]))


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    replace_with_retry(temporary, path)


def replace_with_retry(source: Path, destination: Path, attempts: int = 8) -> None:
    """Tolerate brief Windows antivirus/OneDrive locks without losing progress."""
    for attempt in range(attempts):
        try:
            source.replace(destination)
            return
        except PermissionError:
            if attempt + 1 == attempts:
                raise
            time.sleep(0.25 * (attempt + 1))


def archive_path(output: Path, symbol: str, day: str) -> Path:
    safe_symbol = "".join(character for character in symbol if character.isalnum() or character in ".-")
    return output / day[:4] / day / f"{safe_symbol}.json.gz"


def fetch_chain(symbol: str, day: str, api_key: str) -> Dict[str, Any]:
    response = get_alpha_vantage_response(
        {"function": "HISTORICAL_OPTIONS", "symbol": symbol, "date": day},
        api_key,
        timeout=90,
    )
    payload = response.json()
    message = payload.get("Error Message") or payload.get("Note") or payload.get("Information")
    if message:
        raise RuntimeError(message)
    if not isinstance(payload.get("data"), list):
        raise ValueError("Alpha Vantage response lacks options data")
    return payload


def write_gzip_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=6) as handle:
        json.dump(payload, handle, separators=(",", ":"))
    replace_with_retry(temporary, path)


def run(items: Iterable[Tuple[str, str]], api_key: str, output: Path, delay: float = 0.5) -> Dict[str, Any]:
    manifest_path = output / "manifest.json"
    manifest = {"status": "running", "completed": [], "unavailable": [], "failed": []}
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        for field in ("completed", "unavailable"):
            manifest[field] = list(dict.fromkeys(previous.get(field, [])))
    completed = set(manifest["completed"])
    unavailable = set(manifest["unavailable"])
    for symbol, day in items:
        key = f"{symbol}|{day}"
        destination = archive_path(output, symbol, day)
        if key in completed or key in unavailable or destination.exists():
            continue
        try:
            payload = fetch_chain(symbol, day, api_key)
            write_gzip_json(destination, payload)
            manifest["completed"].append(key)
            completed.add(key)
            print(f"DONE {key}: {len(payload['data'])} contracts")
        except ValueError as exc:
            if "lacks options data" not in str(exc):
                raise
            manifest["unavailable"].append(key)
            unavailable.add(key)
            print(f"UNAVAILABLE {key}")
        except Exception as exc:
            manifest["status"] = "failed_closed"
            manifest["failed"].append({"request": key, "error": safe_error(exc, api_key)})
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
    parser.add_argument("--limit-requests", type=int, default=0)
    parser.add_argument("--delay-seconds", type=float, default=0.5)
    parser.add_argument("--market-date-only", action="store_true")
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    items = event_requests(
        read_jsonl(args.events), args.role, include_future_date=not args.market_date_only,
        start_date=args.start_date, end_date=args.end_date,
    )
    if args.limit_requests:
        items = items[: args.limit_requests]
    result = run(items, api_key, args.output, args.delay_seconds)
    print(json.dumps({"status": result["status"], "requests": len(items), "completed": len(result["completed"]), "unavailable": len(result["unavailable"])}, indent=2))


if __name__ == "__main__":
    main()
