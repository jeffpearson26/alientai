from __future__ import annotations

"""Independently content-audit the full active-Nasdaq daily archive."""

import argparse
import gzip
import json
from datetime import date
from pathlib import Path
from typing import Any

from download_alpha_vantage_full_nasdaq_daily import (
    canonical_universe_bytes,
    load_listing_rows,
    series_filename,
    sha256_bytes,
    sha256_file,
    validate_payload,
)


def ten_year_boundary(latest: date) -> date:
    try:
        return latest.replace(year=latest.year - 10)
    except ValueError:
        return latest.replace(year=latest.year - 10, day=28)


def read_gzip_json(path: Path) -> tuple[dict[str, Any], bytes]:
    with gzip.open(path, "rb") as handle:
        content = handle.read()
    return json.loads(content), content


def audit(
    archive: Path,
    listing_status: Path,
    *,
    expected_latest_date: str,
) -> dict[str, Any]:
    universe = load_listing_rows(listing_status)
    expected_symbols = {row["symbol"] for row in universe}
    manifest_path = archive / "manifest.json"
    universe_path = archive / "universe.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frozen_universe = json.loads(universe_path.read_text(encoding="utf-8"))
    failures: dict[str, str] = {}
    audited: dict[str, dict[str, Any]] = {}
    completed = dict(manifest.get("completed") or {})
    unavailable = dict(manifest.get("unavailable") or {})
    recorded_failed = dict(manifest.get("failed") or {})
    overlap = sorted(set(completed) & set(unavailable))
    accounted = set(completed) | set(unavailable) | set(recorded_failed)
    expected_universe_hash = sha256_bytes(canonical_universe_bytes(universe))
    contract_ok = (
        manifest.get("schema_version") == 1
        and manifest.get("status") == "complete"
        and manifest.get("provider") == "Alpha Vantage"
        and manifest.get("endpoint") == "TIME_SERIES_DAILY_ADJUSTED"
        and manifest.get("outputsize") == "full"
        and manifest.get("expected_latest_date") == expected_latest_date
        and manifest.get("listing_status_sha256") == sha256_file(listing_status)
        and manifest.get("universe_sha256") == expected_universe_hash
        and manifest.get("universe_count") == len(universe)
        and frozen_universe.get("universe_sha256") == expected_universe_hash
        and frozen_universe.get("rows") == universe
        and not overlap
        and accounted == expected_symbols
        and not recorded_failed
    )
    expected_files = {
        series_filename(symbol)
        for symbol in completed
    }
    actual_files = {path.name for path in (archive / "series").glob("*.json.gz")}
    orphan_files = sorted(actual_files - expected_files)
    missing_files = sorted(expected_files - actual_files)
    expected_latest = date.fromisoformat(expected_latest_date)
    boundary = ten_year_boundary(expected_latest)
    seasoned_symbols = {
        row["symbol"]
        for row in universe
        if row["ipo_date"]
        and row["ipo_date"].lower() != "null"
        and date.fromisoformat(row["ipo_date"]) <= boundary
    }
    ten_year_gaps: dict[str, str] = {}
    stale_symbols: dict[str, str] = {}
    for symbol, record in completed.items():
        path = archive / str(record.get("path") or "")
        try:
            if path.resolve().parent != (archive / "series").resolve():
                raise ValueError("series path escapes the archive series directory")
            payload, content = read_gzip_json(path)
            details = validate_payload(
                payload,
                symbol,
                expected_latest_date=expected_latest_date,
            )
            if record.get("content_sha256") != sha256_bytes(content):
                raise ValueError("content SHA-256 mismatch")
            for field in ("rows", "first_date", "latest_date", "freshness"):
                if record.get(field) != details.get(field):
                    raise ValueError(f"manifest {field} mismatch")
            if details["freshness"] == "stale":
                stale_symbols[symbol] = details["latest_date"]
            if (
                symbol in seasoned_symbols
                and date.fromisoformat(details["first_date"]) > boundary
            ):
                ten_year_gaps[symbol] = details["first_date"]
            audited[symbol] = details
        except Exception as exc:
            failures[symbol] = str(exc)
    integrity_pass = (
        contract_ok
        and not failures
        and not orphan_files
        and not missing_files
        and len(audited) == len(completed)
    )
    status = (
        "FAIL"
        if not integrity_pass
        else (
            "PASS_WITH_EXPLICIT_GAPS"
            if unavailable or stale_symbols or ten_year_gaps
            else "PASS"
        )
    )
    return {
        "status": status,
        "integrity_pass": integrity_pass,
        "research_only": True,
        "execution_enabled": False,
        "provider": "Alpha Vantage",
        "endpoint": "TIME_SERIES_DAILY_ADJUSTED",
        "outputsize": "full",
        "expected_latest_date": expected_latest_date,
        "listing_status_path": str(listing_status.resolve()),
        "listing_status_sha256": sha256_file(listing_status),
        "universe_sha256": expected_universe_hash,
        "universe_count": len(universe),
        "stock_count": sum(row["asset_type"] == "Stock" for row in universe),
        "etf_count": sum(row["asset_type"] == "ETF" for row in universe),
        "completed_count": len(completed),
        "unavailable_count": len(unavailable),
        "recorded_failed_count": len(recorded_failed),
        "current_count": len(audited) - len(stale_symbols),
        "stale_count": len(stale_symbols),
        "stale_symbols": stale_symbols,
        "ten_year_eligible_count": len(seasoned_symbols),
        "ten_year_pass_count": len(seasoned_symbols - set(ten_year_gaps)),
        "ten_year_gap_count": len(ten_year_gaps),
        "ten_year_gaps": ten_year_gaps,
        "younger_listing_count": len(expected_symbols - seasoned_symbols),
        "unavailable": unavailable,
        "failures": failures,
        "overlap": overlap,
        "orphan_files": orphan_files,
        "missing_files": missing_files,
        "manifest_path": str(manifest_path.resolve()),
        "manifest_sha256": sha256_file(manifest_path),
        "universe_path": str(universe_path.resolve()),
        "universe_file_sha256": sha256_file(universe_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--listing-status", type=Path, required=True)
    parser.add_argument("--expected-latest-date", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(
        args.archive,
        args.listing_status,
        expected_latest_date=args.expected_latest_date,
    )
    output = args.output or args.archive / "content_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "status",
                    "integrity_pass",
                    "universe_count",
                    "stock_count",
                    "etf_count",
                    "completed_count",
                    "unavailable_count",
                    "current_count",
                    "stale_count",
                    "ten_year_eligible_count",
                    "ten_year_pass_count",
                    "ten_year_gap_count",
                    "younger_listing_count",
                    "recorded_failed_count",
                )
            },
            indent=2,
        )
    )
    if not result["integrity_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
