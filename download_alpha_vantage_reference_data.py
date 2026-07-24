from __future__ import annotations

"""Archive small Alpha Vantage reference/calendar datasets with timestamps."""

import argparse
import gzip
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

from alpha_vantage_http import get_alpha_vantage_response, redact_sensitive_text


ROOT = Path(__file__).resolve().parent


def requests_to_archive(listing_dates: List[str] | None = None) -> List[Tuple[str, Dict[str, str]]]:
    requests = [
        ("listing_status_active", {"function": "LISTING_STATUS", "state": "active"}),
        ("listing_status_delisted", {"function": "LISTING_STATUS", "state": "delisted"}),
        ("earnings_calendar_12month", {"function": "EARNINGS_CALENDAR", "horizon": "12month"}),
        ("ipo_calendar", {"function": "IPO_CALENDAR"}),
    ]
    for listing_date in listing_dates or []:
        try:
            datetime.strptime(listing_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"listing date must be YYYY-MM-DD: {listing_date}") from exc
        requests.append((f"listing_status_active_{listing_date}", {"function": "LISTING_STATUS", "state": "active", "date": listing_date}))
    return requests


def safe_message(value: Any, api_key: str) -> str:
    return redact_sensitive_text(value or "request failed", api_key)


def fetch(params: Dict[str, str], api_key: str) -> bytes:
    response = get_alpha_vantage_response(params, api_key, timeout=90)
    content = response.content
    if not content.strip():
        raise ValueError("empty Alpha Vantage response")
    if content.lstrip().startswith(b"{"):
        payload = response.json()
        message = payload.get("Error Message") or payload.get("Note") or payload.get("Information")
        if message:
            raise RuntimeError(message)
    return content


def write_gzip(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wb", compresslevel=6) as handle:
        handle.write(content)
    temporary.replace(path)


def run(output: Path, api_key: str, *, listing_dates: List[str] | None = None, delay_seconds: float = 0.0) -> Dict[str, Any]:
    collected_at = datetime.now(timezone.utc)
    day = collected_at.date().isoformat()
    manifest = {"status": "complete", "collected_at_utc": collected_at.isoformat(), "files": []}
    for name, params in requests_to_archive(listing_dates):
        content = fetch(params, api_key)
        destination = output / day / f"{name}.csv.gz"
        write_gzip(destination, content)
        manifest["files"].append({
            "name": name, "path": str(destination), "bytes_uncompressed": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        })
        print(f"DONE {name}: {len(content)} bytes")
        if delay_seconds:
            time.sleep(delay_seconds)
    manifest_path = output / day / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--listing-dates-file", type=Path)
    parser.add_argument("--delay-seconds", type=float, default=0.75)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    try:
        listing_dates = args.listing_dates_file.read_text(encoding="utf-8").split() if args.listing_dates_file else None
        result = run(args.output, api_key, listing_dates=listing_dates, delay_seconds=args.delay_seconds)
    except Exception as exc:
        raise RuntimeError(safe_message(exc, api_key)) from exc
    print(json.dumps({"status": result["status"], "files": len(result["files"])}, indent=2))


if __name__ == "__main__":
    main()
