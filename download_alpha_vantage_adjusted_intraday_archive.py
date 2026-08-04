from __future__ import annotations

"""Download an immutable, adjusted monthly intraday research archive.

This collector is intentionally separate from the existing raw/as-traded
collectors.  It is designed for leakage-safe rolling-horizon model research,
not for current-session scoring or execution.
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from dotenv import load_dotenv

from alpha_vantage_http import get_alpha_vantage_response, redact_sensitive_text


ROOT = Path(__file__).resolve().parent
DATASET_NAME = "rolling_20m_nasdaq101_adjusted"
SCHEMA_VERSION = 1


class HistoricalMonthUnavailable(ValueError):
    """The provider returned no historical candles for a valid request."""


def month_range(start_month: str, end_month: str) -> List[str]:
    start = datetime.strptime(start_month, "%Y-%m")
    end = datetime.strptime(end_month, "%Y-%m")
    if start > end:
        raise ValueError("start month must not be after end month")
    output: List[str] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        output.append(f"{year:04d}-{month:02d}")
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return output


def read_symbols(path: Path, benchmarks: Iterable[str] = ()) -> List[str]:
    symbols = {
        line.strip().upper()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    symbols.update(str(value or "").strip().upper() for value in benchmarks)
    symbols.discard("")
    if not symbols:
        raise ValueError("symbols file contains no symbols")
    return sorted(symbols)


def symbols_sha256(symbols: Sequence[str]) -> str:
    return hashlib.sha256(("\n".join(symbols) + "\n").encode("utf-8")).hexdigest()


def request_items(symbols: Sequence[str], months: Sequence[str]) -> List[Tuple[str, str]]:
    return [(symbol, month) for month in months for symbol in symbols]


def request_id(symbol: str, month: str) -> str:
    return f"{symbol}|{month}"


def archive_path(output: Path, symbol: str, month: str) -> Path:
    safe_symbol = "".join(
        character for character in symbol if character.isalnum() or character in ".-"
    )
    return output / month[:4] / month / f"{safe_symbol}.csv.gz"


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
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )
    replace_with_retry(temporary, path)


def ensure_free_space(path: Path, minimum_free_gb: float) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if minimum_free_gb <= 0:
        return
    free_bytes = shutil.disk_usage(path).free
    if free_bytes < minimum_free_gb * 1024**3:
        raise RuntimeError(
            f"low disk space: {free_bytes / 1024**3:.2f} GB free; "
            f"requires at least {minimum_free_gb:.2f} GB"
        )


def provider_message(content: bytes) -> str:
    if not content.lstrip().startswith(b"{"):
        return ""
    try:
        payload = json.loads(content.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return ""
    return str(
        payload.get("Error Message")
        or payload.get("Note")
        or payload.get("Information")
        or ""
    )


def is_unavailable_message(message: str) -> bool:
    lowered = str(message or "").casefold()
    return (
        "invalid api call" in lowered
        and "please retry or visit the documentation" in lowered
    )


def validate_csv_content(content: bytes, expected_month: str) -> Dict[str, Any]:
    if not content.strip():
        raise HistoricalMonthUnavailable("empty historical intraday response")
    message = provider_message(content)
    if message:
        if is_unavailable_message(message):
            raise HistoricalMonthUnavailable("historical intraday month unavailable")
        raise RuntimeError(message)

    text = content.decode("utf-8-sig", errors="strict")
    reader = csv.DictReader(io.StringIO(text))
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise ValueError("Alpha Vantage response lacks required intraday columns")

    timestamps = set()
    first_timestamp = ""
    last_timestamp = ""
    row_count = 0
    for row in reader:
        timestamp_text = str(row.get("timestamp") or "").strip()
        timestamp = datetime.strptime(timestamp_text, "%Y-%m-%d %H:%M:%S")
        if timestamp.strftime("%Y-%m") != expected_month:
            raise ValueError("Alpha Vantage response contains a mismatched month")
        if timestamp.minute % 5 or timestamp.second or timestamp.microsecond:
            raise ValueError("Alpha Vantage response contains an off-grid timestamp")
        if timestamp_text in timestamps:
            raise ValueError("Alpha Vantage response contains duplicate timestamps")
        timestamps.add(timestamp_text)

        open_value = float(row["open"])
        high_value = float(row["high"])
        low_value = float(row["low"])
        close_value = float(row["close"])
        volume = int(float(row["volume"]))
        if min(open_value, high_value, low_value, close_value) <= 0:
            raise ValueError("Alpha Vantage response contains a nonpositive price")
        if high_value < max(open_value, low_value, close_value):
            raise ValueError("Alpha Vantage response contains an invalid high")
        if low_value > min(open_value, high_value, close_value):
            raise ValueError("Alpha Vantage response contains an invalid low")
        if volume < 0:
            raise ValueError("Alpha Vantage response contains negative volume")

        first_timestamp = min(first_timestamp or timestamp_text, timestamp_text)
        last_timestamp = max(last_timestamp or timestamp_text, timestamp_text)
        row_count += 1

    if row_count == 0:
        raise HistoricalMonthUnavailable("historical intraday month has no rows")
    return {
        "rows": row_count,
        "first_timestamp_et": first_timestamp,
        "last_timestamp_et": last_timestamp,
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "uncompressed_bytes": len(content),
    }


def fetch_month(symbol: str, month: str, api_key: str) -> Tuple[bytes, Dict[str, Any]]:
    response = get_alpha_vantage_response(
        {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": "5min",
            "month": month,
            "outputsize": "full",
            "adjusted": "true",
            "extended_hours": "true",
            "datatype": "csv",
        },
        api_key,
        timeout=180,
    )
    content = response.content
    return content, validate_csv_content(content, month)


def write_gzip(path: Path, content: bytes) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wb", compresslevel=6) as handle:
        handle.write(content)
    replace_with_retry(temporary, path)
    return path.stat().st_size


def validate_existing(path: Path, expected_month: str) -> Dict[str, Any]:
    with gzip.open(path, "rb") as handle:
        content = handle.read()
    metadata = validate_csv_content(content, expected_month)
    metadata["compressed_bytes"] = path.stat().st_size
    return metadata


def manifest_contract(
    symbols: Sequence[str],
    start_month: str,
    end_month: str,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset": DATASET_NAME,
        "research_only": True,
        "execution_enabled": False,
        "source": "alpha_vantage",
        "function": "TIME_SERIES_INTRADAY",
        "interval": "5min",
        "adjusted": True,
        "extended_hours": True,
        "timestamp_timezone": "America/New_York",
        "timestamp_convention": "interval_start",
        "start_month": start_month,
        "end_month": end_month,
        "symbols_count": len(symbols),
        "symbols_sha256": symbols_sha256(symbols),
        "request_count": len(symbols) * len(month_range(start_month, end_month)),
    }


def new_manifest(contract: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **contract,
        "status": "running",
        "completed": [],
        "unavailable": [],
        "failed": [],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def load_manifest(path: Path, contract: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return new_manifest(contract)
    previous = json.loads(path.read_text(encoding="utf-8"))
    for key, expected in contract.items():
        if previous.get(key) != expected:
            raise ValueError(f"archive manifest contract mismatch: {key}")
    manifest = new_manifest(contract)
    manifest["created_at_utc"] = previous.get(
        "created_at_utc", manifest["created_at_utc"]
    )
    for field in ("completed", "unavailable"):
        manifest[field] = list(previous.get(field, []))
    return manifest


def safe_error(value: Any, api_key: str) -> str:
    return redact_sensitive_text(
        value or "Alpha Vantage adjusted intraday request failed", api_key
    )


def run(
    *,
    symbols: Sequence[str],
    start_month: str,
    end_month: str,
    api_key: str,
    output: Path,
    delay_seconds: float,
    minimum_free_gb: float,
    limit_requests: int = 0,
) -> Dict[str, Any]:
    months = month_range(start_month, end_month)
    items = request_items(symbols, months)
    contract = manifest_contract(symbols, start_month, end_month)
    manifest_path = output / "manifest.json"
    manifest = load_manifest(manifest_path, contract)

    completed = {
        str(item.get("request") or ""): item
        for item in manifest["completed"]
        if isinstance(item, dict)
    }
    unavailable = {
        str(item.get("request") or ""): item
        for item in manifest["unavailable"]
        if isinstance(item, dict)
    }
    pending = [
        item
        for item in items
        if request_id(*item) not in completed
        and request_id(*item) not in unavailable
    ]
    selected = pending[:limit_requests] if limit_requests else pending

    for symbol, month in selected:
        item_id = request_id(symbol, month)
        destination = archive_path(output, symbol, month)
        try:
            ensure_free_space(output, minimum_free_gb)
            if destination.exists():
                metadata = validate_existing(destination, month)
                action = "ADOPTED"
            else:
                content, metadata = fetch_month(symbol, month, api_key)
                metadata["compressed_bytes"] = write_gzip(destination, content)
                action = "DONE"
            record = {
                "request": item_id,
                "symbol": symbol,
                "month": month,
                "relative_path": destination.relative_to(output).as_posix(),
                **metadata,
            }
            manifest["completed"].append(record)
            completed[item_id] = record
            print(
                f"{action} {item_id}: {metadata['rows']} rows, "
                f"{metadata['compressed_bytes']} compressed bytes",
                flush=True,
            )
        except HistoricalMonthUnavailable as exc:
            record = {
                "request": item_id,
                "symbol": symbol,
                "month": month,
                "reason": str(exc),
            }
            manifest["unavailable"].append(record)
            unavailable[item_id] = record
            print(f"UNAVAILABLE {item_id}", flush=True)
        except Exception as exc:
            manifest["status"] = "failed_closed"
            manifest["failed"] = [
                {"request": item_id, "error": safe_error(exc, api_key)}
            ]
            manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_json(manifest_path, manifest)
            raise

        manifest["failed"] = []
        manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_json(manifest_path, manifest)
        if delay_seconds:
            time.sleep(delay_seconds)

    accounted = len(completed) + len(unavailable)
    if accounted == contract["request_count"]:
        manifest["status"] = "complete"
    elif limit_requests:
        manifest["status"] = "partial_limit"
    else:
        manifest["status"] = "running"
    manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    atomic_json(manifest_path, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-month", default="2020-01")
    parser.add_argument("--end-month", required=True)
    parser.add_argument("--benchmarks", default="QQQ,SPY")
    parser.add_argument("--delay-seconds", type=float, default=0.85)
    parser.add_argument("--minimum-free-gb", type=float, default=100.0)
    parser.add_argument("--limit-requests", type=int, default=0)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    benchmarks = [
        value.strip().upper()
        for value in str(args.benchmarks or "").split(",")
        if value.strip()
    ]
    symbols = read_symbols(args.symbols_file, benchmarks)
    result = run(
        symbols=symbols,
        start_month=args.start_month,
        end_month=args.end_month,
        api_key=api_key,
        output=args.output,
        delay_seconds=args.delay_seconds,
        minimum_free_gb=args.minimum_free_gb,
        limit_requests=args.limit_requests,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "requests": result["request_count"],
                "completed": len(result["completed"]),
                "unavailable": len(result["unavailable"]),
                "failed": len(result["failed"]),
                "output": str(args.output.resolve()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
