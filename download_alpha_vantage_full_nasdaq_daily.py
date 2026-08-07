from __future__ import annotations

"""Collect full adjusted-daily Alpha Vantage history for active Nasdaq listings.

The collector freezes its universe from a preserved Alpha Vantage
``LISTING_STATUS`` response, stores every series on drive D, checkpoints after
every symbol, and distinguishes provider-unavailable, stale, and failed rows.
It is research-only and has no broker, order, engine, or settings dependency.
"""

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import shutil
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

from alpha_vantage_http import (
    AlphaVantageRequestError,
    get_alpha_vantage_response,
    redact_sensitive_text,
)


ROOT = Path(__file__).resolve().parent
ENDPOINT = "TIME_SERIES_DAILY_ADJUSTED"
OUTPUTSIZE = "full"
MINIMUM_FREE_BYTES = 20 * 1024**3
REQUIRED_FIELDS = (
    "1. open",
    "2. high",
    "3. low",
    "4. close",
    "5. adjusted close",
    "6. volume",
    "7. dividend amount",
    "8. split coefficient",
)


class ProviderUnavailableError(RuntimeError):
    """The provider explicitly has no adjusted-daily series for a symbol."""


class RetryableProviderError(RuntimeError):
    """The provider returned a temporary/rate/entitlement message."""


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def atomic_write_gzip(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wb", compresslevel=6) as handle:
        handle.write(content)
    temporary.replace(path)


def load_listing_rows(path: Path) -> list[dict[str, str]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "symbol",
            "name",
            "exchange",
            "assetType",
            "ipoDate",
            "status",
        }
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                f"listing status is missing columns: "
                f"{sorted(required - set(reader.fieldnames or []))}"
            )
        rows = []
        for source_row in reader:
            if str(source_row.get("exchange") or "").strip().upper() != "NASDAQ":
                continue
            asset_type = str(source_row.get("assetType") or "").strip()
            if asset_type.upper() not in {"STOCK", "ETF"}:
                continue
            if str(source_row.get("status") or "").strip().upper() != "ACTIVE":
                continue
            symbol = str(source_row.get("symbol") or "").strip().upper()
            if not symbol:
                raise ValueError("active Nasdaq listing has a blank symbol")
            rows.append(
                {
                    "symbol": symbol,
                    "name": str(source_row.get("name") or "").strip(),
                    "exchange": "NASDAQ",
                    "asset_type": "ETF" if asset_type.upper() == "ETF" else "Stock",
                    "ipo_date": str(source_row.get("ipoDate") or "").strip(),
                    "status": "Active",
                }
            )
    rows.sort(key=lambda row: row["symbol"])
    symbols = [row["symbol"] for row in rows]
    if not rows or len(symbols) != len(set(symbols)):
        raise ValueError("filtered active Nasdaq symbols must be nonempty and unique")
    filenames = [series_filename(symbol) for symbol in symbols]
    if len(filenames) != len(set(filenames)):
        raise ValueError("series filename collision in Nasdaq universe")
    return rows


def canonical_universe_bytes(rows: Iterable[dict[str, str]]) -> bytes:
    return (
        json.dumps(list(rows), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def series_filename(symbol: str) -> str:
    identity = hashlib.sha256(symbol.encode("utf-8")).hexdigest()
    return f"{identity}.json.gz"


def time_series(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    matches = [
        value
        for key, value in payload.items()
        if str(key).startswith("Time Series") and isinstance(value, dict)
    ]
    if len(matches) != 1 or not matches[0]:
        raise ValueError("payload must contain exactly one nonempty time series")
    return matches[0]


def validate_payload(
    payload: dict[str, Any],
    symbol: str,
    *,
    expected_latest_date: str,
) -> dict[str, Any]:
    payload_symbol = str(
        (payload.get("Meta Data") or {}).get("2. Symbol") or ""
    ).strip().upper()
    if payload_symbol != symbol:
        raise ValueError(
            f"payload symbol {payload_symbol!r}; expected {symbol!r}"
        )
    series = time_series(payload)
    parsed_dates: list[date] = []
    for market_date, row in series.items():
        try:
            parsed_date = date.fromisoformat(str(market_date))
        except ValueError as exc:
            raise ValueError(f"invalid market date {market_date!r}") from exc
        if not isinstance(row, dict) or not all(field in row for field in REQUIRED_FIELDS):
            raise ValueError(f"{market_date}: missing adjusted-daily fields")
        try:
            values = {field: float(row[field]) for field in REQUIRED_FIELDS}
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{market_date}: nonnumeric adjusted-daily field") from exc
        if any(not math.isfinite(value) for value in values.values()):
            raise ValueError(f"{market_date}: nonfinite adjusted-daily field")
        open_price = values["1. open"]
        high = values["2. high"]
        low = values["3. low"]
        close = values["4. close"]
        adjusted = values["5. adjusted close"]
        if (
            min(open_price, high, low, close, adjusted) <= 0.0
            or values["6. volume"] < 0.0
            or values["7. dividend amount"] < 0.0
            or values["8. split coefficient"] <= 0.0
            or high < max(open_price, low, close)
            or low > min(open_price, high, close)
        ):
            raise ValueError(f"{market_date}: invalid adjusted-daily row")
        parsed_dates.append(parsed_date)
    first_date = min(parsed_dates)
    latest_date = max(parsed_dates)
    expected = date.fromisoformat(expected_latest_date)
    if latest_date > expected:
        raise ValueError(
            f"latest date {latest_date} is after expected completed session {expected}"
        )
    return {
        "rows": len(parsed_dates),
        "first_date": first_date.isoformat(),
        "latest_date": latest_date.isoformat(),
        "freshness": "current" if latest_date == expected else "stale",
    }


def fetch_payload(symbol: str, api_key: str) -> dict[str, Any]:
    response = get_alpha_vantage_response(
        {
            "function": ENDPOINT,
            "symbol": symbol,
            "outputsize": OUTPUTSIZE,
        },
        api_key,
        timeout=120,
    )
    payload = response.json()
    if isinstance(payload, dict) and any(
        str(key).startswith("Time Series") for key in payload
    ):
        return payload
    if not isinstance(payload, dict):
        raise RetryableProviderError("daily response was not a JSON object")
    error = payload.get("Error Message")
    if error:
        raise ProviderUnavailableError(str(error))
    message = payload.get("Note") or payload.get("Information")
    raise RetryableProviderError(str(message or "daily response had no time series"))


def _seed_path(seed_archive: Path, symbol: str) -> Path:
    safe = symbol.replace("/", "-").replace(".", "-")
    return seed_archive / f"{safe}_daily.json"


def _canonical_payload(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def ensure_d_drive(output: Path) -> None:
    resolved = output.resolve()
    if resolved.drive.upper() != "D:":
        raise ValueError(f"large archive output must be on drive D: {resolved}")
    free = shutil.disk_usage(resolved.anchor).free
    if free < MINIMUM_FREE_BYTES:
        raise RuntimeError(
            f"drive D has {free / 1024**3:.2f} GiB free; 20 GiB required"
        )


def initial_manifest(
    listing_status: Path,
    universe: list[dict[str, str]],
    expected_latest_date: str,
    seed_archive: Path | None,
) -> dict[str, Any]:
    universe_bytes = canonical_universe_bytes(universe)
    return {
        "schema_version": 1,
        "status": "running",
        "research_only": True,
        "execution_enabled": False,
        "provider": "Alpha Vantage",
        "endpoint": ENDPOINT,
        "outputsize": OUTPUTSIZE,
        "expected_latest_date": expected_latest_date,
        "listing_status_path": str(listing_status.resolve()),
        "listing_status_sha256": sha256_file(listing_status),
        "universe_sha256": sha256_bytes(universe_bytes),
        "universe_count": len(universe),
        "asset_type_counts": {
            "Stock": sum(row["asset_type"] == "Stock" for row in universe),
            "ETF": sum(row["asset_type"] == "ETF" for row in universe),
        },
        "seed_archive": str(seed_archive.resolve()) if seed_archive else None,
        "seed_manifest_sha256": (
            sha256_file(seed_archive / "manifest.json")
            if seed_archive and (seed_archive / "manifest.json").exists()
            else None
        ),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "completed_at_utc": None,
        "completed": {},
        "unavailable": {},
        "failed": {},
    }


def verify_resume_contract(
    manifest: dict[str, Any],
    listing_status: Path,
    universe: list[dict[str, str]],
    expected_latest_date: str,
    seed_archive: Path | None,
) -> None:
    expected = initial_manifest(
        listing_status, universe, expected_latest_date, seed_archive
    )
    fields = (
        "schema_version",
        "provider",
        "endpoint",
        "outputsize",
        "expected_latest_date",
        "listing_status_sha256",
        "universe_sha256",
        "universe_count",
        "asset_type_counts",
        "seed_archive",
        "seed_manifest_sha256",
    )
    mismatches = [
        field for field in fields if manifest.get(field) != expected.get(field)
    ]
    if mismatches:
        raise ValueError(f"resume manifest contract mismatch: {mismatches}")


def checkpoint(path: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    atomic_write_json(path, manifest)


def run(
    *,
    listing_status: Path,
    output: Path,
    expected_latest_date: str,
    api_key: str,
    delay_seconds: float,
    retries: int,
    retry_wait_seconds: float,
    seed_archive: Path | None = None,
) -> dict[str, Any]:
    date.fromisoformat(expected_latest_date)
    universe = load_listing_rows(listing_status)
    ensure_d_drive(output)
    output.mkdir(parents=True, exist_ok=True)
    series_dir = output / "series"
    series_dir.mkdir(exist_ok=True)
    manifest_path = output / "manifest.json"
    universe_path = output / "universe.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        verify_resume_contract(
            manifest,
            listing_status,
            universe,
            expected_latest_date,
            seed_archive,
        )
    else:
        orphans = list(series_dir.glob("*.json.gz"))
        if orphans:
            raise ValueError("series files exist without a resumable manifest")
        manifest = initial_manifest(
            listing_status,
            universe,
            expected_latest_date,
            seed_archive,
        )
        atomic_write_json(
            universe_path,
            {
                "schema_version": 1,
                "provider": "Alpha Vantage",
                "source_listing_sha256": manifest["listing_status_sha256"],
                "universe_sha256": manifest["universe_sha256"],
                "rows": universe,
            },
        )
        checkpoint(manifest_path, manifest)
    by_symbol = {row["symbol"]: row for row in universe}
    for index, symbol in enumerate(by_symbol, 1):
        if symbol in manifest["completed"] or symbol in manifest["unavailable"]:
            continue
        manifest["failed"].pop(symbol, None)
        destination = series_dir / series_filename(symbol)
        payload: dict[str, Any] | None = None
        origin = "provider"
        if seed_archive:
            seed_path = _seed_path(seed_archive, symbol)
            if seed_path.exists():
                try:
                    candidate = json.loads(seed_path.read_text(encoding="utf-8"))
                    details = validate_payload(
                        candidate,
                        symbol,
                        expected_latest_date=expected_latest_date,
                    )
                    if details["freshness"] == "current":
                        payload = candidate
                        origin = "seed_archive"
                except Exception:
                    payload = None
        try:
            if payload is None:
                last_error: Exception | None = None
                for attempt in range(1, retries + 1):
                    try:
                        payload = fetch_payload(symbol, api_key)
                        break
                    except ProviderUnavailableError:
                        raise
                    except (AlphaVantageRequestError, RetryableProviderError) as exc:
                        last_error = exc
                        if attempt == retries:
                            raise
                        time.sleep(retry_wait_seconds * (2 ** (attempt - 1)))
                if payload is None:
                    raise RuntimeError(str(last_error or "request returned no payload"))
            details = validate_payload(
                payload,
                symbol,
                expected_latest_date=expected_latest_date,
            )
            content = _canonical_payload(payload)
            atomic_write_gzip(destination, content)
            manifest["completed"][symbol] = {
                **by_symbol[symbol],
                **details,
                "path": str(destination.relative_to(output)).replace("\\", "/"),
                "content_sha256": sha256_bytes(content),
                "bytes_uncompressed": len(content),
                "origin": origin,
            }
            print(
                f"[{index}/{len(universe)}] {symbol}: saved "
                f"{details['rows']} rows through {details['latest_date']} "
                f"({details['freshness']}, {origin})",
                flush=True,
            )
        except ProviderUnavailableError as exc:
            manifest["unavailable"][symbol] = {
                **by_symbol[symbol],
                "reason": redact_sensitive_text(exc, api_key),
            }
            print(
                f"[{index}/{len(universe)}] {symbol}: unavailable",
                flush=True,
            )
        except Exception as exc:
            manifest["failed"][symbol] = {
                **by_symbol[symbol],
                "reason": redact_sensitive_text(exc, api_key),
            }
            print(
                f"[{index}/{len(universe)}] {symbol}: ERROR "
                f"{redact_sensitive_text(exc, api_key)}",
                flush=True,
            )
        checkpoint(manifest_path, manifest)
        if delay_seconds > 0 and origin == "provider":
            time.sleep(delay_seconds)
    accounted = set(manifest["completed"]) | set(manifest["unavailable"])
    manifest["status"] = (
        "complete"
        if accounted == set(by_symbol) and not manifest["failed"]
        else "failed_closed"
    )
    manifest["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    checkpoint(manifest_path, manifest)
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "universe": len(universe),
                "completed": len(manifest["completed"]),
                "unavailable": len(manifest["unavailable"]),
                "failed": len(manifest["failed"]),
                "current": sum(
                    item.get("freshness") == "current"
                    for item in manifest["completed"].values()
                ),
                "stale": sum(
                    item.get("freshness") == "stale"
                    for item in manifest["completed"].values()
                ),
            },
            indent=2,
        ),
        flush=True,
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listing-status", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-latest-date", required=True)
    parser.add_argument("--seed-archive", type=Path)
    parser.add_argument("--delay-seconds", type=float, default=0.75)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--retry-wait-seconds", type=float, default=2.0)
    args = parser.parse_args()
    if args.delay_seconds < 0 or args.retries < 1 or args.retry_wait_seconds < 0:
        raise ValueError("delay/retry values are invalid")
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    run(
        listing_status=args.listing_status,
        output=args.output,
        expected_latest_date=args.expected_latest_date,
        api_key=api_key,
        delay_seconds=args.delay_seconds,
        retries=args.retries,
        retry_wait_seconds=args.retry_wait_seconds,
        seed_archive=args.seed_archive,
    )


if __name__ == "__main__":
    main()
