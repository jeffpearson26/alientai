from __future__ import annotations

"""Content-audit a source-pure Alpha Vantage adjusted-daily archive."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence


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


def read_symbols(path: Path) -> list[str]:
    symbols = [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not symbols or len(symbols) != len(set(symbols)):
        raise ValueError("symbols must be nonempty and unique")
    return symbols


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _series(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    matches = [
        value
        for key, value in payload.items()
        if str(key).startswith("Time Series") and isinstance(value, dict)
    ]
    if len(matches) != 1 or not matches[0]:
        raise ValueError("payload must contain one nonempty time series")
    return matches[0]


def _valid_row(row: dict[str, Any]) -> bool:
    if not all(field in row for field in REQUIRED_FIELDS):
        return False
    try:
        values = {field: float(row[field]) for field in REQUIRED_FIELDS}
    except (TypeError, ValueError):
        return False
    if any(not math.isfinite(value) for value in values.values()):
        return False
    open_price = values["1. open"]
    high = values["2. high"]
    low = values["3. low"]
    close = values["4. close"]
    adjusted = values["5. adjusted close"]
    return (
        min(open_price, high, low, close, adjusted) > 0.0
        and values["6. volume"] >= 0.0
        and values["7. dividend amount"] >= 0.0
        and values["8. split coefficient"] > 0.0
        and high >= max(open_price, low, close)
        and low <= min(open_price, high, close)
    )


def audit_archive(
    archive: Path,
    symbols: Sequence[str],
    *,
    required_latest_date: str,
) -> dict[str, Any]:
    manifest_path = archive / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = list(symbols)
    failures: dict[str, str] = {}
    files: dict[str, dict[str, Any]] = {}
    common_dates: set[str] | None = None
    expected_filenames = {
        f"{symbol.replace('/', '-').replace('.', '-')}_daily.json"
        for symbol in expected
    }
    orphan_files = sorted(
        path.name
        for path in archive.glob("*_daily.json")
        if path.name not in expected_filenames
    )
    for symbol in expected:
        path = archive / (
            f"{symbol.replace('/', '-').replace('.', '-')}_daily.json"
        )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload_symbol = str(
                (payload.get("Meta Data") or {}).get("2. Symbol") or ""
            ).upper()
            if payload_symbol != symbol:
                raise ValueError(
                    f"payload symbol {payload_symbol!r}; expected {symbol!r}"
                )
            series = _series(payload)
            invalid_dates = sorted(
                market_date
                for market_date, row in series.items()
                if not isinstance(row, dict) or not _valid_row(row)
            )
            if invalid_dates:
                raise ValueError(
                    f"{len(invalid_dates)} invalid rows; first={invalid_dates[0]}"
                )
            dates = set(series)
            latest = max(dates)
            if latest != required_latest_date:
                raise ValueError(
                    f"latest date {latest}; required {required_latest_date}"
                )
            common_dates = dates if common_dates is None else common_dates & dates
            files[symbol] = {
                "path": str(path.resolve()),
                "sha256": sha256(path),
                "rows": len(series),
                "first_date": min(dates),
                "latest_date": latest,
            }
        except Exception as exc:
            failures[symbol] = str(exc)
    manifest_symbols = list(manifest.get("completed") or [])
    manifest_ok = (
        manifest.get("status") == "complete"
        and manifest.get("function") == "TIME_SERIES_DAILY_ADJUSTED"
        and manifest.get("outputsize") == "full"
        and not manifest.get("failed")
        and manifest_symbols == expected
    )
    status = (
        "PASS"
        if manifest_ok
        and not failures
        and not orphan_files
        and len(files) == len(expected)
        and bool(common_dates)
        else "FAIL"
    )
    return {
        "status": status,
        "research_only": True,
        "execution_enabled": False,
        "provider": "Alpha Vantage",
        "endpoint": "TIME_SERIES_DAILY_ADJUSTED",
        "outputsize": "full",
        "required_latest_date": required_latest_date,
        "expected_symbols": len(expected),
        "audited_symbols": len(files),
        "manifest_ok": manifest_ok,
        "failures": failures,
        "orphan_files": orphan_files,
        "minimum_rows": min(
            (details["rows"] for details in files.values()), default=0
        ),
        "maximum_rows": max(
            (details["rows"] for details in files.values()), default=0
        ),
        "common_date_count": len(common_dates or set()),
        "common_first_date": min(common_dates) if common_dates else None,
        "common_latest_date": max(common_dates) if common_dates else None,
        "manifest_path": str(manifest_path.resolve()),
        "manifest_sha256": sha256(manifest_path),
        "files": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--required-latest-date", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit_archive(
        args.archive,
        read_symbols(args.symbols_file),
        required_latest_date=args.required_latest_date,
    )
    output = args.output or args.archive / "content_audit.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "status",
                    "expected_symbols",
                    "audited_symbols",
                    "minimum_rows",
                    "maximum_rows",
                    "common_date_count",
                    "common_first_date",
                    "common_latest_date",
                    "failures",
                )
            },
            indent=2,
        )
    )
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
