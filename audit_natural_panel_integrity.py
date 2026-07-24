"""Fail-closed integrity audit for the natural five-day research panel.

This only reads a JSONL panel and writes a small audit report.  It never
changes source data, models, settings, or execution state.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


def _date(value: object) -> str:
    return str(value or "")[:10]


def audit(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    keys = [(str(row.get("symbol", "")).upper(), _date(row.get("market_date"))) for row in rows]
    duplicate_keys = sum(count - 1 for count in Counter(keys).values() if count > 1)
    bad_identity = sum(not symbol or not market_date for symbol, market_date in keys)
    bad_label_dates = 0
    bad_as_of = 0
    future_short_interest = 0
    missing_option = 0
    missing_short_interest = 0
    for row, (_, market_date) in zip(rows, keys):
        future_date = _date(row.get("future_market_date"))
        as_of_date = _date(row.get("as_of_utc"))
        if not future_date or future_date <= market_date:
            bad_label_dates += 1
        if not as_of_date or as_of_date > market_date:
            bad_as_of += 1
        if not bool(row.get("option_available")):
            missing_option += 1
        if not bool(row.get("short_interest_available")):
            missing_short_interest += 1
        available = _date(row.get("short_interest_available_at_utc"))
        if bool(row.get("short_interest_available")) and (not available or available > market_date):
            future_short_interest += 1
    failures = {
        "duplicate_symbol_market_date_keys": duplicate_keys,
        "invalid_identity": bad_identity,
        "invalid_or_nonfuture_label_date": bad_label_dates,
        "as_of_after_market_date": bad_as_of,
        "short_interest_after_decision": future_short_interest,
    }
    return {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "rows": len(rows),
        "unique_symbol_market_date_keys": len(set(keys)),
        "option_available_rows": len(rows) - missing_option,
        "short_interest_available_rows": len(rows) - missing_short_interest,
        "failures": failures,
        "passes": not any(failures.values()),
    }


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(read_jsonl(args.panel))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
