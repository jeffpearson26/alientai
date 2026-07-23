from __future__ import annotations

"""Normalize FINRA-style short-interest files with explicit availability dates.

This importer deliberately does not download from FINRA.  The caller supplies
the published file and the publication timestamp so settlement information
cannot be mistaken for information available to a historical model.
"""

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def parse_iso(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a UTC offset or Z")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def number(value: Any) -> float | None:
    try:
        result = float(str(value).replace(",", ""))
        return result if result >= 0 else None
    except (TypeError, ValueError):
        return None


def normalize(row: Mapping[str, Any], *, symbol_column: str, shares_column: str,
              settlement_date: str, publication_timestamp_utc: str) -> dict[str, Any] | None:
    symbol = str(row.get(symbol_column) or "").upper().strip()
    shares = number(row.get(shares_column))
    if not symbol or shares is None:
        return None
    return {
        "symbol": symbol, "settlement_date": settlement_date,
        "available_at_utc": publication_timestamp_utc, "short_interest_shares": shares,
        "source": "FINRA_EQUITY_SHORT_INTEREST", "research_only": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a downloaded FINRA-style short-interest CSV safely.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--symbol-column", required=True)
    parser.add_argument("--shares-column", required=True)
    parser.add_argument("--settlement-date", required=True)
    parser.add_argument("--publication-timestamp-utc", required=True)
    args = parser.parse_args()
    publication = parse_iso(args.publication_timestamp_utc)
    rows = []
    with args.input.open("r", newline="", encoding="utf-8-sig") as handle:
        for raw in csv.DictReader(handle):
            item = normalize(raw, symbol_column=args.symbol_column, shares_column=args.shares_column,
                             settlement_date=args.settlement_date, publication_timestamp_utc=publication)
            if item is not None:
                rows.append(item)
    if not rows:
        raise ValueError("no valid short-interest rows were found")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({"status": "complete", "research_only": True, "rows": len(rows),
                      "publication_timestamp_utc": publication, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
