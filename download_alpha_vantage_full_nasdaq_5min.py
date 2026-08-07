from __future__ import annotations

"""Build a resumable ten-year five-minute archive for active Nasdaq listings.

The archive is research-only.  It uses a frozen universe, immutable contract,
append-only request ledger, hashed filenames, and explicit unavailable states.
Only Alpha Vantage's adjusted TIME_SERIES_INTRADAY OHLCV fields are sourced.
VWAP and trade count remain blank unless the provider actually supplies them.
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from alpha_vantage_http import AlphaVantageRequestError, redact_sensitive_text
from download_alpha_vantage_adjusted_intraday_archive import (
    HistoricalMonthUnavailable,
    fetch_month,
    month_range,
    validate_csv_content,
)


ROOT = Path(__file__).resolve().parent
SCHEMA_VERSION = 1
INTERVAL = "5min"
PROVIDER = "Alpha Vantage"
ENDPOINT = "TIME_SERIES_INTRADAY"
NORMALIZED_FIELDS = (
    "timestamp",
    "ticker",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "vwap",
    "number_of_trades",
    "vwap_available",
    "number_of_trades_available",
)
DEFAULT_BLACKOUTS_PT = (
    ("04:20", "06:50"),
    ("08:20", "08:45"),
    ("13:20", "14:50"),
)
PACIFIC = ZoneInfo("America/Los_Angeles")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def ensure_d_drive(path: Path, minimum_free_gib: float) -> None:
    path.mkdir(parents=True, exist_ok=True)
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise ValueError(f"large archive output must be on drive D: {resolved}")
    free = shutil.disk_usage(resolved.anchor).free
    if free < minimum_free_gib * 1024**3:
        raise RuntimeError(
            f"drive D has {free / 1024**3:.2f} GiB free; "
            f"{minimum_free_gib:.2f} GiB required"
        )


def load_frozen_universe(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = list(payload.get("rows") or [])
    normalized: list[dict[str, str]] = []
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            raise ValueError("frozen universe contains a blank symbol")
        normalized.append(
            {
                "symbol": symbol,
                "name": str(row.get("name") or "").strip(),
                "exchange": str(row.get("exchange") or "").strip(),
                "asset_type": str(row.get("asset_type") or "").strip(),
                "ipo_date": str(row.get("ipo_date") or "").strip(),
                "status": str(row.get("status") or "").strip(),
            }
        )
    if not normalized:
        raise ValueError("frozen universe is empty")
    symbols = [row["symbol"] for row in normalized]
    if symbols != sorted(symbols) or len(symbols) != len(set(symbols)):
        raise ValueError("frozen universe symbols must be sorted and unique")
    return normalized


def canonical_universe_sha256(rows: Iterable[dict[str, str]]) -> str:
    content = (
        json.dumps(list(rows), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    return sha256_bytes(content)


def request_key(symbol: str, month: str) -> str:
    return f"{symbol}|{month}"


def series_relative_path(symbol: str, month: str) -> Path:
    identity = hashlib.sha256(symbol.encode("utf-8")).hexdigest()
    return Path(month[:4]) / month / f"{identity}.csv.gz"


def parse_optional_float(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    number = float(text)
    if not math.isfinite(number) or number < 0:
        raise ValueError("optional numeric field is invalid")
    return text


def parse_optional_integer(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    number = float(text)
    if not math.isfinite(number) or number < 0 or not number.is_integer():
        raise ValueError("optional trade-count field is invalid")
    return str(int(number))


def normalize_provider_csv(
    content: bytes,
    *,
    symbol: str,
    month: str,
) -> tuple[bytes, dict[str, Any]]:
    source_details = validate_csv_content(content, month, INTERVAL)
    reader = csv.DictReader(
        io.StringIO(content.decode("utf-8-sig", errors="strict"))
    )
    source_fields = set(reader.fieldnames or [])
    vwap_field = "vwap" if "vwap" in source_fields else None
    trades_field = next(
        (
            field
            for field in ("number_of_trades", "trade_count", "transactions")
            if field in source_fields
        ),
        None,
    )
    rows: list[dict[str, str]] = []
    vwap_rows = 0
    trade_rows = 0
    for source in reader:
        vwap = parse_optional_float(source.get(vwap_field)) if vwap_field else ""
        trades = (
            parse_optional_integer(source.get(trades_field))
            if trades_field
            else ""
        )
        vwap_rows += bool(vwap)
        trade_rows += bool(trades)
        rows.append(
            {
                "timestamp": str(source["timestamp"]).strip(),
                "ticker": symbol,
                "open": str(source["open"]).strip(),
                "high": str(source["high"]).strip(),
                "low": str(source["low"]).strip(),
                "close": str(source["close"]).strip(),
                "volume": str(source["volume"]).strip(),
                "vwap": vwap,
                "number_of_trades": trades,
                "vwap_available": "true" if vwap else "false",
                "number_of_trades_available": "true" if trades else "false",
            }
        )
    rows.sort(key=lambda row: row["timestamp"])
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=NORMALIZED_FIELDS,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    normalized = output.getvalue().encode("utf-8")
    return normalized, {
        "rows": len(rows),
        "first_timestamp_et": rows[0]["timestamp"],
        "last_timestamp_et": rows[-1]["timestamp"],
        "source_sha256": source_details["content_sha256"],
        "normalized_sha256": sha256_bytes(normalized),
        "source_uncompressed_bytes": len(content),
        "normalized_uncompressed_bytes": len(normalized),
        "vwap_rows": int(vwap_rows),
        "number_of_trades_rows": int(trade_rows),
    }


def write_gzip_atomic(path: Path, content: bytes) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wb", compresslevel=6) as handle:
        handle.write(content)
    temporary.replace(path)
    return path.stat().st_size


def read_latest_ledger(path: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return latest
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid ledger JSON at line {line_number}"
                ) from exc
            key = str(record.get("request") or "")
            if not key:
                raise ValueError(f"ledger line {line_number} lacks request")
            latest[key] = record
    return latest


def append_ledger(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _clock_minutes(value: str) -> int:
    parsed = datetime.strptime(value, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def provider_blackout_remaining_seconds(
    now: datetime,
    windows: Iterable[tuple[str, str]] = DEFAULT_BLACKOUTS_PT,
) -> float:
    local = now.astimezone(PACIFIC)
    if local.weekday() >= 5:
        return 0.0
    minute = local.hour * 60 + local.minute
    second = local.second + local.microsecond / 1_000_000
    for start_text, end_text in windows:
        start = _clock_minutes(start_text)
        end = _clock_minutes(end_text)
        if start <= minute < end:
            return max(0.0, (end - minute) * 60 - second)
    return 0.0


def wait_for_provider_window() -> None:
    announced = False
    while True:
        remaining = provider_blackout_remaining_seconds(
            datetime.now(timezone.utc)
        )
        if remaining <= 0:
            return
        if not announced:
            print(
                "PAUSED for frozen prospective-program Alpha Vantage window; "
                f"approximately {remaining / 60:.1f} minutes remain",
                flush=True,
            )
            announced = True
        time.sleep(min(60.0, remaining + 0.1))


def is_retryable_provider_message(exc: Exception) -> bool:
    lowered = str(exc).casefold()
    return any(
        token in lowered
        for token in (
            "rate limit",
            "call frequency",
            "thank you for using alpha vantage",
            "higher api call frequency",
            "temporarily",
            "timeout",
            "connection",
        )
    )


def fetch_with_retry(
    symbol: str,
    month: str,
    api_key: str,
    *,
    attempts: int,
    retry_wait_seconds: float,
) -> tuple[bytes, dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        wait_for_provider_window()
        try:
            return fetch_month(symbol, month, api_key, INTERVAL)
        except HistoricalMonthUnavailable:
            raise
        except (AlphaVantageRequestError, RuntimeError) as exc:
            last_error = exc
            if (
                attempt == attempts
                or (
                    isinstance(exc, RuntimeError)
                    and not is_retryable_provider_message(exc)
                )
            ):
                raise
            time.sleep(retry_wait_seconds * (2 ** (attempt - 1)))
    raise RuntimeError(str(last_error or "provider request failed"))


def seed_states(seed_archive: Path | None) -> dict[str, dict[str, Any]]:
    if not seed_archive:
        return {}
    manifest_path = seed_archive / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {
        "status": "complete",
        "source": "alpha_vantage",
        "function": ENDPOINT,
        "interval": INTERVAL,
        "adjusted": True,
        "extended_hours": True,
    }
    mismatches = [
        key for key, expected in required.items() if manifest.get(key) != expected
    ]
    if mismatches:
        raise ValueError(f"seed archive contract mismatch: {mismatches}")
    states: dict[str, dict[str, Any]] = {}
    for state in ("completed", "unavailable"):
        for record in manifest.get(state, []):
            if isinstance(record, dict) and record.get("request"):
                states[str(record["request"])] = {
                    **record,
                    "state": state,
                }
    return states


def build_contract(
    *,
    universe_path: Path,
    rows: list[dict[str, str]],
    start_month: str,
    end_month: str,
    seed_archive: Path | None,
) -> dict[str, Any]:
    months = month_range(start_month, end_month)
    return {
        "schema_version": SCHEMA_VERSION,
        "research_only": True,
        "execution_enabled": False,
        "provider": PROVIDER,
        "endpoint": ENDPOINT,
        "interval": INTERVAL,
        "adjusted": True,
        "extended_hours": True,
        "timestamp_timezone": "America/New_York",
        "timestamp_convention": "interval_start",
        "source_fields": ["timestamp", "open", "high", "low", "close", "volume"],
        "normalized_fields": list(NORMALIZED_FIELDS),
        "vwap_policy": "blank_unless_supplied_by_provider",
        "number_of_trades_policy": "blank_unless_supplied_by_provider",
        "corporate_action_policy": (
            "adjusted intraday OHLCV; explicit dividends/splits live in the "
            "paired adjusted-daily archive"
        ),
        "start_month": start_month,
        "end_month": end_month,
        "month_count": len(months),
        "universe_path": str(universe_path.resolve()),
        "universe_file_sha256": sha256_file(universe_path),
        "universe_sha256": canonical_universe_sha256(rows),
        "universe_count": len(rows),
        "stock_count": sum(row["asset_type"] == "Stock" for row in rows),
        "etf_count": sum(row["asset_type"] == "ETF" for row in rows),
        "request_count": len(rows) * len(months),
        "provider_blackouts_pt_weekdays": [
            {"start": start, "end": end}
            for start, end in DEFAULT_BLACKOUTS_PT
        ],
        "seed_archive": str(seed_archive.resolve()) if seed_archive else None,
        "seed_manifest_sha256": (
            sha256_file(seed_archive / "manifest.json")
            if seed_archive
            else None
        ),
    }


def load_or_create_contract(
    path: Path,
    expected: dict[str, Any],
) -> dict[str, Any]:
    if path.exists():
        actual = json.loads(path.read_text(encoding="utf-8"))
        if actual != expected:
            differing = sorted(
                key
                for key in set(actual) | set(expected)
                if actual.get(key) != expected.get(key)
            )
            raise ValueError(f"archive contract mismatch: {differing}")
        return actual
    atomic_json(path, expected)
    return expected


def counts_from_states(
    states: dict[str, dict[str, Any]],
) -> dict[str, int]:
    return {
        state: sum(record.get("state") == state for record in states.values())
        for state in ("completed", "unavailable", "failed")
    }


def validate_final_states(
    states: dict[str, dict[str, Any]],
    *,
    symbols: Iterable[str],
    months: Iterable[str],
) -> None:
    expected = {
        request_key(symbol, month)
        for month in months
        for symbol in symbols
    }
    extra = sorted(set(states) - expected)
    if extra:
        raise ValueError(f"ledger contains out-of-contract requests: {extra[:5]}")
    for key, record in states.items():
        symbol, month = key.rsplit("|", 1)
        if (
            record.get("symbol", symbol) != symbol
            or record.get("month", month) != month
            or record.get("state") not in {"completed", "unavailable", "failed"}
        ):
            raise ValueError(f"ledger final state is malformed: {key}")


def write_summary(
    path: Path,
    *,
    contract: dict[str, Any],
    states: dict[str, dict[str, Any]],
    status: str,
    started_at_utc: str,
) -> dict[str, Any]:
    counts = counts_from_states(states)
    accounted = counts["completed"] + counts["unavailable"]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "started_at_utc": started_at_utc,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "request_count": contract["request_count"],
        "completed_count": counts["completed"],
        "unavailable_count": counts["unavailable"],
        "failed_count": counts["failed"],
        "accounted_count": accounted,
        "pending_count": contract["request_count"] - accounted,
    }
    if status == "complete":
        payload["completed_at_utc"] = payload["updated_at_utc"]
    atomic_json(path, payload)
    return payload


def validate_adopted_normalized(
    path: Path,
    *,
    symbol: str,
    month: str,
) -> dict[str, Any]:
    from audit_alpha_vantage_full_nasdaq_5min import validate_normalized_content

    with gzip.open(path, "rb") as handle:
        content = handle.read()
    return validate_normalized_content(content, symbol=symbol, month=month)


def run(
    *,
    universe_path: Path,
    output: Path,
    start_month: str,
    end_month: str,
    api_key: str,
    delay_seconds: float,
    minimum_free_gib: float,
    retries: int,
    retry_wait_seconds: float,
    seed_archive: Path | None,
    limit_requests: int = 0,
) -> dict[str, Any]:
    rows = load_frozen_universe(universe_path)
    months = month_range(start_month, end_month)
    ensure_d_drive(output, minimum_free_gib)
    output.mkdir(parents=True, exist_ok=True)
    contract = load_or_create_contract(
        output / "contract.json",
        build_contract(
            universe_path=universe_path,
            rows=rows,
            start_month=start_month,
            end_month=end_month,
            seed_archive=seed_archive,
        ),
    )
    ledger_path = output / "ledger.jsonl"
    summary_path = output / "summary.json"
    states = read_latest_ledger(ledger_path)
    universe_symbols = [row["symbol"] for row in rows]
    validate_final_states(states, symbols=universe_symbols, months=months)
    seeds = seed_states(seed_archive)
    started_at = (
        json.loads(summary_path.read_text(encoding="utf-8")).get(
            "started_at_utc"
        )
        if summary_path.exists()
        else datetime.now(timezone.utc).isoformat()
    )
    write_summary(
        summary_path,
        contract=contract,
        states=states,
        status="running",
        started_at_utc=started_at,
    )
    processed = 0
    for month in months:
        for symbol in universe_symbols:
            key = request_key(symbol, month)
            if states.get(key, {}).get("state") in {"completed", "unavailable"}:
                continue
            if limit_requests and processed >= limit_requests:
                return write_summary(
                    summary_path,
                    contract=contract,
                    states=states,
                    status="partial_limit",
                    started_at_utc=started_at,
                )
            processed += 1
            destination = output / "series" / series_relative_path(symbol, month)
            timestamp = datetime.now(timezone.utc).isoformat()
            try:
                ensure_d_drive(output, minimum_free_gib)
                origin = "provider"
                if destination.exists():
                    details = validate_adopted_normalized(
                        destination,
                        symbol=symbol,
                        month=month,
                    )
                    details["normalized_sha256"] = details.pop("content_sha256")
                    details["compressed_bytes"] = destination.stat().st_size
                    details.setdefault("source_sha256", None)
                    details.setdefault("source_uncompressed_bytes", None)
                    origin = "adopted_local"
                elif key in seeds and seeds[key]["state"] == "completed":
                    seed_record = seeds[key]
                    seed_path = seed_archive / str(seed_record["relative_path"])
                    with gzip.open(seed_path, "rb") as handle:
                        source = handle.read()
                    normalized, details = normalize_provider_csv(
                        source,
                        symbol=symbol,
                        month=month,
                    )
                    details["compressed_bytes"] = write_gzip_atomic(
                        destination, normalized
                    )
                    origin = "seed_archive"
                elif key in seeds and seeds[key]["state"] == "unavailable":
                    record = {
                        "request": key,
                        "symbol": symbol,
                        "month": month,
                        "state": "unavailable",
                        "origin": "seed_archive",
                        "reason": str(seeds[key].get("reason") or "unavailable"),
                        "recorded_at_utc": timestamp,
                    }
                    append_ledger(ledger_path, record)
                    states[key] = record
                    print(f"UNAVAILABLE {key} (seed archive)", flush=True)
                    write_summary(
                        summary_path,
                        contract=contract,
                        states=states,
                        status="running",
                        started_at_utc=started_at,
                    )
                    continue
                else:
                    source, _ = fetch_with_retry(
                        symbol,
                        month,
                        api_key,
                        attempts=retries,
                        retry_wait_seconds=retry_wait_seconds,
                    )
                    normalized, details = normalize_provider_csv(
                        source,
                        symbol=symbol,
                        month=month,
                    )
                    details["compressed_bytes"] = write_gzip_atomic(
                        destination, normalized
                    )
                record = {
                    "request": key,
                    "symbol": symbol,
                    "month": month,
                    "state": "completed",
                    "origin": origin,
                    "relative_path": str(
                        destination.relative_to(output)
                    ).replace("\\", "/"),
                    "recorded_at_utc": timestamp,
                    **details,
                }
                append_ledger(ledger_path, record)
                states[key] = record
                print(
                    f"DONE {key}: {record['rows']} rows ({origin})",
                    flush=True,
                )
            except HistoricalMonthUnavailable as exc:
                record = {
                    "request": key,
                    "symbol": symbol,
                    "month": month,
                    "state": "unavailable",
                    "origin": "provider",
                    "reason": str(exc),
                    "recorded_at_utc": timestamp,
                }
                append_ledger(ledger_path, record)
                states[key] = record
                print(f"UNAVAILABLE {key}", flush=True)
            except Exception as exc:
                record = {
                    "request": key,
                    "symbol": symbol,
                    "month": month,
                    "state": "failed",
                    "reason": redact_sensitive_text(exc, api_key),
                    "recorded_at_utc": timestamp,
                }
                append_ledger(ledger_path, record)
                states[key] = record
                write_summary(
                    summary_path,
                    contract=contract,
                    states=states,
                    status="failed_closed",
                    started_at_utc=started_at,
                )
                raise
            write_summary(
                summary_path,
                contract=contract,
                states=states,
                status="running",
                started_at_utc=started_at,
            )
            if delay_seconds > 0 and states[key].get("origin") == "provider":
                time.sleep(delay_seconds)
    counts = counts_from_states(states)
    complete = (
        counts["completed"] + counts["unavailable"]
        == contract["request_count"]
        and counts["failed"] == 0
    )
    return write_summary(
        summary_path,
        contract=contract,
        states=states,
        status="complete" if complete else "failed_closed",
        started_at_utc=started_at,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-month", default="2016-08")
    parser.add_argument("--end-month", default="2026-07")
    parser.add_argument("--seed-archive", type=Path)
    parser.add_argument("--delay-seconds", type=float, default=0.75)
    parser.add_argument("--minimum-free-gib", type=float, default=300.0)
    parser.add_argument("--retries", type=int, default=6)
    parser.add_argument("--retry-wait-seconds", type=float, default=5.0)
    parser.add_argument("--limit-requests", type=int, default=0)
    args = parser.parse_args()
    if (
        args.delay_seconds < 0
        or args.minimum_free_gib < 0
        or args.retries < 1
        or args.retry_wait_seconds < 0
        or args.limit_requests < 0
    ):
        raise ValueError("delay, disk, retry, or limit argument is invalid")
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    result = run(
        universe_path=args.universe,
        output=args.output,
        start_month=args.start_month,
        end_month=args.end_month,
        api_key=api_key,
        delay_seconds=args.delay_seconds,
        minimum_free_gib=args.minimum_free_gib,
        retries=args.retries,
        retry_wait_seconds=args.retry_wait_seconds,
        seed_archive=args.seed_archive,
        limit_requests=args.limit_requests,
    )
    print(json.dumps(result, indent=2), flush=True)
    if result["status"] not in {"complete", "partial_limit"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
