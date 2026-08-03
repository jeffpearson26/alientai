from __future__ import annotations

"""Archive monthly five-minute extended-hours candles for matched research events."""

import argparse
import gzip
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from alpha_vantage_http import get_alpha_vantage_response, redact_sensitive_text


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
    return redact_sensitive_text(value or "Alpha Vantage intraday request failed", api_key)


def unavailable_response(value: Any) -> bool:
    message = str(value or "").casefold()
    return "invalid api call" in message and "please retry or visit the documentation" in message


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
    response = get_alpha_vantage_response(
        {
            "function": "TIME_SERIES_INTRADAY", "symbol": symbol, "interval": "5min",
            "month": month, "outputsize": "full", "adjusted": "false",
            "extended_hours": "true", "datatype": "csv",
        },
        api_key,
        timeout=120,
    )
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


def fetch_current(symbol: str, api_key: str, entitlement: str) -> bytes:
    """Fetch the current trailing intraday window with an explicit freshness contract."""
    if entitlement not in {"realtime", "delayed"}:
        raise ValueError("current intraday entitlement must be realtime or delayed")
    response = get_alpha_vantage_response(
        {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": "5min",
            "outputsize": "full",
            "adjusted": "false",
            "extended_hours": "true",
            "entitlement": entitlement,
            "datatype": "csv",
        },
        api_key,
        timeout=120,
    )
    content = response.content
    if not content.strip():
        raise ValueError("Alpha Vantage response lacks intraday data")
    if content.lstrip().startswith(b"{"):
        payload = response.json()
        message = (
            payload.get("Error Message")
            or payload.get("Note")
            or payload.get("Information")
        )
        if message:
            raise RuntimeError(message)
    header = content.splitlines()[0].decode(
        "utf-8-sig", errors="replace"
    ).casefold()
    if not all(
        field in header
        for field in ("timestamp", "open", "high", "low", "close", "volume")
    ):
        raise ValueError("Alpha Vantage response lacks intraday data")
    return content


def validate_current_request(
    rows: Iterable[Dict[str, Any]],
    current_date: str,
    now_utc: datetime | None = None,
) -> None:
    """Reject early, stale, or mixed-date realtime snapshots."""
    parsed_date = datetime.strptime(current_date, "%Y-%m-%d").date()
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("current request clock must be timezone-aware")
    eastern_date = now.astimezone(ZoneInfo("America/New_York")).date()
    if parsed_date != eastern_date:
        raise ValueError("current-date must equal today's U.S. Eastern date")
    selected = list(rows)
    if not selected:
        raise ValueError("current request contains no events")
    market_dates = {str(row.get("market_date") or "") for row in selected}
    if market_dates != {current_date}:
        raise ValueError("current request contains a mixed or stale market date")
    cutoffs = []
    for row in selected:
        value = str(row.get("as_of_utc") or "")
        cutoff = datetime.fromisoformat(value)
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("current event cutoff must be timezone-aware")
        cutoffs.append(cutoff.astimezone(timezone.utc))
    if now.astimezone(timezone.utc) < max(cutoffs):
        raise ValueError("current intraday request is earlier than the event cutoff")


def run_current(
    symbols: Iterable[str],
    current_date: str,
    api_key: str,
    output: Path,
    entitlement: str,
    delay: float = 0.75,
    minimum_free_gb: float = 0.0,
) -> Dict[str, Any]:
    """Archive one explicitly entitled current snapshot per symbol."""
    month = current_date[:7]
    manifest_path = output / "manifest.json"
    manifest = {
        "status": "running",
        "mode": "current",
        "entitlement": entitlement,
        "current_date": current_date,
        "completed": [],
        "unavailable": [],
        "failed": [],
    }
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        frozen = {
            key: previous.get(key)
            for key in ("mode", "entitlement", "current_date")
        }
        expected = {
            "mode": "current",
            "entitlement": entitlement,
            "current_date": current_date,
        }
        if frozen != expected:
            raise ValueError("current snapshot manifest contract mismatch")
        for field in ("completed", "unavailable"):
            manifest[field] = list(dict.fromkeys(previous.get(field, [])))
    completed = set(manifest["completed"])
    unavailable = set(manifest["unavailable"])
    for symbol in sorted(set(symbols)):
        request_id = f"{symbol}|{current_date}|{entitlement}"
        destination = archive_path(output, symbol, month)
        if request_id in completed or request_id in unavailable or destination.exists():
            continue
        try:
            ensure_free_space(output, minimum_free_gb)
            content = fetch_current(symbol, api_key, entitlement)
            write_gzip(destination, content)
            manifest["completed"].append(request_id)
            completed.add(request_id)
            print(f"DONE {request_id}: {len(content)} bytes", flush=True)
        except (ValueError, RuntimeError) as exc:
            if "lacks intraday data" not in str(exc) and not unavailable_response(exc):
                raise
            manifest["unavailable"].append(request_id)
            unavailable.add(request_id)
            print(f"UNAVAILABLE {request_id}", flush=True)
        except Exception as exc:
            manifest["status"] = "failed_closed"
            manifest["failed"].append(
                {"request": request_id, "error": safe_error(exc, api_key)}
            )
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


def write_gzip(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wb", compresslevel=6) as handle:
        handle.write(content)
    replace_with_retry(temporary, path)


def ensure_free_space(path: Path, minimum_free_gb: float) -> None:
    if minimum_free_gb <= 0:
        return
    path.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(path).free
    required_bytes = minimum_free_gb * 1024 ** 3
    if free_bytes < required_bytes:
        raise RuntimeError(
            f"low disk space: {free_bytes / 1024 ** 3:.2f} GB free; "
            f"requires at least {minimum_free_gb:.2f} GB"
        )


def run(
    items: Iterable[Tuple[str, str]], api_key: str, output: Path, delay: float = 0.75,
    minimum_free_gb: float = 0.0,
) -> Dict[str, Any]:
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
            ensure_free_space(output, minimum_free_gb)
            content = fetch_month(symbol, month, api_key)
            write_gzip(destination, content)
            manifest["completed"].append(request_id)
            completed.add(request_id)
            print(f"DONE {request_id}: {len(content)} bytes", flush=True)
        except (ValueError, RuntimeError) as exc:
            if "lacks intraday data" not in str(exc) and not unavailable_response(exc):
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
    parser.add_argument("--minimum-free-gb", type=float, default=6.0)
    parser.add_argument(
        "--entitlement",
        choices=("historical", "realtime", "delayed"),
        default="historical",
    )
    parser.add_argument("--current-date")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    event_rows = read_jsonl(args.events)
    items = event_requests(event_rows, args.role)
    if args.entitlement == "historical":
        if args.current_date:
            raise ValueError("--current-date requires realtime or delayed entitlement")
        if args.limit_requests:
            items = items[: args.limit_requests]
        result = run(
            items,
            api_key,
            args.output,
            args.delay_seconds,
            args.minimum_free_gb,
        )
        request_count = len(items)
    else:
        if not args.current_date:
            raise ValueError(
                "--current-date is required for realtime or delayed entitlement"
            )
        validate_current_request(event_rows, args.current_date)
        current_symbols = sorted(
            {
                str(row.get("symbol") or "").strip().upper()
                for row in event_rows
                if str(row.get("symbol") or "").strip()
            }
        )
        if args.limit_requests:
            current_symbols = current_symbols[: args.limit_requests]
        result = run_current(
            current_symbols,
            args.current_date,
            api_key,
            args.output,
            args.entitlement,
            args.delay_seconds,
            args.minimum_free_gb,
        )
        request_count = len(current_symbols)
    print(json.dumps({
        "status": result["status"], "requests": request_count,
        "completed": len(result["completed"]), "unavailable": len(result["unavailable"]),
    }, indent=2))


if __name__ == "__main__":
    main()
