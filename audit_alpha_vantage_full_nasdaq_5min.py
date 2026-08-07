from __future__ import annotations

"""Independently content-audit the full active-Nasdaq five-minute archive."""

import argparse
import csv
import gzip
import io
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from download_alpha_vantage_full_nasdaq_5min import (
    ENDPOINT,
    INTERVAL,
    NORMALIZED_FIELDS,
    canonical_universe_sha256,
    load_frozen_universe,
    month_range,
    read_latest_ledger,
    request_key,
    series_relative_path,
    sha256_bytes,
    sha256_file,
)


def validate_normalized_content(
    content: bytes,
    *,
    symbol: str,
    month: str,
) -> dict[str, Any]:
    reader = csv.DictReader(
        io.StringIO(content.decode("utf-8-sig", errors="strict"))
    )
    if tuple(reader.fieldnames or ()) != NORMALIZED_FIELDS:
        raise ValueError("normalized CSV columns do not match the contract")
    timestamps: set[str] = set()
    first = ""
    last = ""
    rows = 0
    vwap_rows = 0
    trade_rows = 0
    for row in reader:
        if str(row.get("ticker") or "") != symbol:
            raise ValueError("normalized CSV ticker mismatch")
        timestamp_text = str(row.get("timestamp") or "")
        timestamp = datetime.strptime(timestamp_text, "%Y-%m-%d %H:%M:%S")
        if (
            timestamp.strftime("%Y-%m") != month
            or timestamp.minute % 5
            or timestamp.second
        ):
            raise ValueError("normalized CSV timestamp violates month/grid")
        if timestamp_text in timestamps:
            raise ValueError("normalized CSV has a duplicate timestamp")
        timestamps.add(timestamp_text)
        values = {
            field: float(row[field])
            for field in ("open", "high", "low", "close", "volume")
        }
        if (
            any(not math.isfinite(value) for value in values.values())
            or min(values["open"], values["high"], values["low"], values["close"])
            <= 0
            or values["volume"] < 0
            or values["high"]
            < max(values["open"], values["low"], values["close"])
            or values["low"]
            > min(values["open"], values["high"], values["close"])
        ):
            raise ValueError("normalized CSV contains invalid OHLCV")
        vwap = str(row.get("vwap") or "")
        trades = str(row.get("number_of_trades") or "")
        vwap_available = str(row.get("vwap_available") or "")
        trades_available = str(row.get("number_of_trades_available") or "")
        if vwap_available not in {"true", "false"} or (
            (vwap_available == "true") != bool(vwap)
        ):
            raise ValueError("VWAP availability flag is inconsistent")
        if trades_available not in {"true", "false"} or (
            (trades_available == "true") != bool(trades)
        ):
            raise ValueError("trade-count availability flag is inconsistent")
        if vwap:
            value = float(vwap)
            if not math.isfinite(value) or value < 0:
                raise ValueError("VWAP is invalid")
            vwap_rows += 1
        if trades:
            value = float(trades)
            if not math.isfinite(value) or value < 0 or not value.is_integer():
                raise ValueError("trade count is invalid")
            trade_rows += 1
        first = min(first or timestamp_text, timestamp_text)
        last = max(last or timestamp_text, timestamp_text)
        rows += 1
    if not rows:
        raise ValueError("normalized CSV has no rows")
    return {
        "rows": rows,
        "first_timestamp_et": first,
        "last_timestamp_et": last,
        "vwap_rows": vwap_rows,
        "number_of_trades_rows": trade_rows,
        "content_sha256": sha256_bytes(content),
    }


def audit(archive: Path, universe_path: Path) -> dict[str, Any]:
    contract_path = archive / "contract.json"
    summary_path = archive / "summary.json"
    ledger_path = archive / "ledger.jsonl"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    rows = load_frozen_universe(universe_path)
    symbols = [row["symbol"] for row in rows]
    months = month_range(contract["start_month"], contract["end_month"])
    expected_keys = {
        request_key(symbol, month)
        for month in months
        for symbol in symbols
    }
    states = read_latest_ledger(ledger_path)
    completed = {
        key: record
        for key, record in states.items()
        if record.get("state") == "completed"
    }
    unavailable = {
        key: record
        for key, record in states.items()
        if record.get("state") == "unavailable"
    }
    failed = {
        key: record
        for key, record in states.items()
        if record.get("state") == "failed"
    }
    accounted = set(completed) | set(unavailable)
    contract_ok = (
        contract.get("schema_version") == 1
        and contract.get("research_only") is True
        and contract.get("execution_enabled") is False
        and contract.get("provider") == "Alpha Vantage"
        and contract.get("endpoint") == ENDPOINT
        and contract.get("interval") == INTERVAL
        and contract.get("adjusted") is True
        and contract.get("extended_hours") is True
        and contract.get("normalized_fields") == list(NORMALIZED_FIELDS)
        and contract.get("universe_file_sha256") == sha256_file(universe_path)
        and contract.get("universe_sha256") == canonical_universe_sha256(rows)
        and contract.get("universe_count") == len(rows)
        and contract.get("month_count") == len(months)
        and contract.get("request_count") == len(expected_keys)
        and summary.get("status") == "complete"
        and summary.get("request_count") == len(expected_keys)
        and accounted == expected_keys
        and not failed
    )
    failures: dict[str, str] = {}
    expected_files: set[str] = set()
    total_rows = 0
    total_vwap_rows = 0
    total_trade_rows = 0
    for key, record in completed.items():
        symbol = str(record.get("symbol") or "")
        month = str(record.get("month") or "")
        expected_relative = (
            Path("series") / series_relative_path(symbol, month)
        ).as_posix()
        relative = str(record.get("relative_path") or "")
        expected_files.add(expected_relative)
        try:
            if relative != expected_relative:
                raise ValueError("ledger relative path mismatch")
            path = archive / Path(relative)
            if not path.is_file():
                raise ValueError("series file is missing")
            if archive.resolve() not in path.resolve().parents:
                raise ValueError("series path escapes archive")
            with gzip.open(path, "rb") as handle:
                content = handle.read()
            details = validate_normalized_content(
                content,
                symbol=symbol,
                month=month,
            )
            if record.get("normalized_sha256") != details["content_sha256"]:
                raise ValueError("normalized SHA-256 mismatch")
            for field in (
                "rows",
                "first_timestamp_et",
                "last_timestamp_et",
                "vwap_rows",
                "number_of_trades_rows",
            ):
                if record.get(field) != details[field]:
                    raise ValueError(f"ledger {field} mismatch")
            total_rows += details["rows"]
            total_vwap_rows += details["vwap_rows"]
            total_trade_rows += details["number_of_trades_rows"]
        except Exception as exc:
            failures[key] = str(exc)
    actual_files = {
        path.relative_to(archive).as_posix()
        for path in (archive / "series").rglob("*.csv.gz")
    }
    orphan_files = sorted(actual_files - expected_files)
    missing_files = sorted(expected_files - actual_files)
    integrity_pass = (
        contract_ok
        and len(completed) + len(unavailable) == len(expected_keys)
        and not failures
        and not orphan_files
        and not missing_files
    )
    return {
        "status": (
            "FAIL"
            if not integrity_pass
            else ("PASS_WITH_EXPLICIT_GAPS" if unavailable else "PASS")
        ),
        "integrity_pass": integrity_pass,
        "research_only": True,
        "execution_enabled": False,
        "provider": "Alpha Vantage",
        "endpoint": ENDPOINT,
        "interval": INTERVAL,
        "adjusted": True,
        "extended_hours": True,
        "universe_count": len(rows),
        "month_count": len(months),
        "request_count": len(expected_keys),
        "completed_count": len(completed),
        "unavailable_count": len(unavailable),
        "failed_count": len(failed),
        "total_rows": total_rows,
        "vwap_rows": total_vwap_rows,
        "number_of_trades_rows": total_trade_rows,
        "failures": failures,
        "orphan_files": orphan_files,
        "missing_files": missing_files,
        "contract_sha256": sha256_file(contract_path),
        "universe_file_sha256": sha256_file(universe_path),
        "ledger_sha256": sha256_file(ledger_path),
        "summary_sha256": sha256_file(summary_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.archive, args.universe)
    output = args.output or args.archive / "content_audit.json"
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
                    "month_count",
                    "request_count",
                    "completed_count",
                    "unavailable_count",
                    "failed_count",
                    "total_rows",
                    "vwap_rows",
                    "number_of_trades_rows",
                )
            },
            indent=2,
        ),
        flush=True,
    )
    if not result["integrity_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
