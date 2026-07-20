from __future__ import annotations

"""Resumable Benzinga analyst-rating archive; makes no calls without an explicit token."""

import argparse
import gzip
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import requests
from dotenv import load_dotenv

from alientai_v2.data.analyst_ratings import normalize_benzinga


ROOT = Path(__file__).resolve().parent
ENDPOINT = "https://api.benzinga.com/api/v2.1/calendar/ratings"


def date_windows(start: date, end: date, window_days: int = 30) -> List[Tuple[date, date]]:
    if end < start or window_days <= 0:
        raise ValueError("valid date range and positive window_days are required")
    output = []
    cursor = start
    while cursor <= end:
        stop = min(end, cursor + timedelta(days=window_days - 1))
        output.append((cursor, stop))
        cursor = stop + timedelta(days=1)
    return output


def safe_error(value: Any, token: str) -> str:
    message = str(value or "Benzinga request failed")
    return message.replace(token, "[REDACTED]")[:1000] if token else message[:1000]


def fetch_window(
    start: date, end: date, token: str, page_size: int = 1000,
) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    page = 0
    while True:
        response = requests.get(
            ENDPOINT,
            params={
                "token": token, "page": page, "pagesize": page_size, "fields": "*",
                "parameters[date_from]": start.isoformat(), "parameters[date_to]": end.isoformat(),
            },
            headers={"accept": "application/json"}, timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("ratings")
        if not isinstance(rows, list):
            raise ValueError("Benzinga response lacks ratings")
        output.extend(dict(row) for row in rows)
        if len(rows) < page_size:
            break
        page += 1
    return output


def archive_path(output: Path, start: date, end: date) -> Path:
    return output / start.strftime("%Y") / f"ratings_{start.isoformat()}_{end.isoformat()}.jsonl.gz"


def write_archive(path: Path, raw_rows: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=6, newline="\n") as handle:
        for raw in raw_rows:
            normalized = normalize_benzinga(raw)
            handle.write(json.dumps({"normalized": normalized, "raw": raw}, separators=(",", ":")) + "\n")
            count += 1
    temporary.replace(path)
    return count


def run(
    windows: Iterable[Tuple[date, date]], token: str, output: Path, page_size: int = 1000,
) -> Dict[str, Any]:
    manifest_path = output / "manifest.json"
    manifest = {"status": "running", "completed": [], "failed": []}
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["completed"] = list(dict.fromkeys(previous.get("completed", [])))
    completed = set(manifest["completed"])
    for start, end in windows:
        key = f"{start.isoformat()}|{end.isoformat()}"
        destination = archive_path(output, start, end)
        if key in completed or destination.exists():
            continue
        try:
            count = write_archive(destination, fetch_window(start, end, token, page_size))
            manifest["completed"].append(key)
            completed.add(key)
            print(f"DONE {key}: {count} ratings", flush=True)
        except Exception as exc:
            manifest["status"] = "failed_closed"
            manifest["failed"].append({"window": key, "error": safe_error(exc, token)})
            manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            raise
        manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["status"] = "complete"
    manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--page-size", type=int, default=1000)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    token = str(os.getenv("BENZINGA_API_KEY") or os.getenv("BENZINGA_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("BENZINGA_API_KEY or BENZINGA_TOKEN is required; no request was made")
    try:
        result = run(date_windows(args.start, args.end, args.window_days), token, args.output, args.page_size)
    except Exception as exc:
        raise RuntimeError(safe_error(exc, token)) from exc
    print(json.dumps({"status": result["status"], "windows": len(result["completed"])}, indent=2))


if __name__ == "__main__":
    main()
