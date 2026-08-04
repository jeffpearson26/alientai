from __future__ import annotations

"""Audit a completed adjusted Alpha Vantage intraday archive end to end."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from download_alpha_vantage_adjusted_intraday_archive import (
    archive_path,
    manifest_contract,
    month_range,
    read_symbols,
    request_id,
    request_items,
    validate_existing,
)


def _records_by_request(
    records: Sequence[Mapping[str, Any]],
    field: str,
) -> dict[str, Mapping[str, Any]]:
    output: dict[str, Mapping[str, Any]] = {}
    for record in records:
        key = str(record.get("request") or "")
        if not key:
            raise ValueError(f"{field} record lacks request")
        if key in output:
            raise ValueError(f"duplicate {field} request: {key}")
        output[key] = record
    return output


def audit_archive(
    output: Path,
    symbols: Sequence[str],
    start_month: str,
    end_month: str,
) -> dict[str, Any]:
    manifest_path = output / "manifest.json"
    if not manifest_path.exists():
        raise ValueError("archive manifest does not exist")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = manifest_contract(symbols, start_month, end_month)
    for field, expected in contract.items():
        if manifest.get(field) != expected:
            raise ValueError(f"archive manifest contract mismatch: {field}")
    if manifest.get("status") != "complete":
        raise ValueError(f"archive is not complete: {manifest.get('status')}")
    if list(manifest.get("failed") or []):
        raise ValueError("archive manifest contains failures")

    completed = _records_by_request(list(manifest.get("completed") or []), "completed")
    unavailable = _records_by_request(
        list(manifest.get("unavailable") or []), "unavailable"
    )
    overlap = sorted(set(completed) & set(unavailable))
    if overlap:
        raise ValueError(f"requests are both completed and unavailable: {overlap[:3]}")

    expected = {
        request_id(symbol, month)
        for symbol, month in request_items(symbols, month_range(start_month, end_month))
    }
    accounted = set(completed) | set(unavailable)
    missing = sorted(expected - accounted)
    unexpected = sorted(accounted - expected)
    if missing or unexpected:
        raise ValueError(
            f"request coverage mismatch: missing={len(missing)} unexpected={len(unexpected)}"
        )

    rows = 0
    compressed_bytes = 0
    uncompressed_bytes = 0
    for index, key in enumerate(sorted(completed), start=1):
        record = completed[key]
        symbol = str(record.get("symbol") or "")
        month = str(record.get("month") or "")
        if key != request_id(symbol, month):
            raise ValueError(f"completed record identity mismatch: {key}")
        path = archive_path(output, symbol, month)
        expected_relative = path.relative_to(output).as_posix()
        if record.get("relative_path") != expected_relative:
            raise ValueError(f"relative path mismatch: {key}")
        if not path.exists():
            raise ValueError(f"completed archive file is missing: {key}")
        metadata = validate_existing(path, month)
        for field in (
            "rows", "first_timestamp_et", "last_timestamp_et",
            "content_sha256", "uncompressed_bytes", "compressed_bytes",
        ):
            if record.get(field) != metadata.get(field):
                raise ValueError(f"metadata mismatch for {key}: {field}")
        rows += int(metadata["rows"])
        compressed_bytes += int(metadata["compressed_bytes"])
        uncompressed_bytes += int(metadata["uncompressed_bytes"])
        if index % 250 == 0:
            print(f"audited {index}/{len(completed)} completed files", flush=True)

    expected_paths = {
        archive_path(
            output,
            str(record["symbol"]),
            str(record["month"]),
        ).resolve()
        for record in completed.values()
    }
    actual_paths = {path.resolve() for path in output.glob("*/*/*.csv.gz")}
    orphan_paths = sorted(str(path) for path in actual_paths - expected_paths)
    if orphan_paths:
        raise ValueError(f"archive contains {len(orphan_paths)} orphan gzip files")

    return {
        "status": "pass",
        "research_only": True,
        "execution_enabled": False,
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive": str(output),
        "request_count": len(expected),
        "completed_count": len(completed),
        "unavailable_count": len(unavailable),
        "failed_count": 0,
        "validated_gzip_files": len(completed),
        "total_rows": rows,
        "compressed_bytes": compressed_bytes,
        "uncompressed_bytes": uncompressed_bytes,
        "orphan_gzip_files": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-month", required=True)
    parser.add_argument("--end-month", required=True)
    parser.add_argument("--benchmarks", default="QQQ,SPY")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    benchmarks = [
        value.strip().upper()
        for value in args.benchmarks.split(",")
        if value.strip()
    ]
    symbols = read_symbols(args.symbols_file, benchmarks)
    report = audit_archive(args.output, symbols, args.start_month, args.end_month)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

