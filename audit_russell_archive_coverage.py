from __future__ import annotations

"""Read-only coverage audit for the legacy Russell daily-candle archive.

This does not train, download, upload, score, or alter trading settings.  It
documents which legacy-list symbols have usable local price history and which
also occur in the current S&P symbol list, so a future Russell experiment can
be constructed deliberately instead of silently mixing universes.
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_DAILY_DIR = ROOT / "data_v2" / "daily_schwab_max_history"
DEFAULT_RUSSELL_SYMBOLS = DEFAULT_DAILY_DIR / "russell2000_symbols_used.txt"
DEFAULT_SP500_SYMBOLS = ROOT / "data_v2" / "sp500_daily_schwab_max_history" / "sp500_symbols_used.txt"


def load_symbols(path: Path) -> set[str]:
    return {
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def csv_date_range(path: Path) -> tuple[str, str]:
    first = ""
    last = ""
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            value = str(row.get("date") or "").strip()
            if value:
                if not first:
                    first = value
                last = value
    return first, last


def audit_archive(daily_dir: Path, russell_symbols: set[str], sp500_symbols: set[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for symbol in sorted(russell_symbols):
        path = daily_dir / f"{symbol.replace('/', '-').replace('.', '-')}_schwab_1d_max.csv"
        if not path.exists():
            missing.append(symbol)
            continue
        first, last = csv_date_range(path)
        if not first or not last:
            missing.append(symbol)
            continue
        rows.append({"symbol": symbol, "first_date": first, "last_date": last, "sp500_overlap": symbol in sp500_symbols})

    latest_distribution = Counter(row["last_date"] for row in rows)
    return {
        "status": "complete",
        "research_only": True,
        "russell_symbols_requested": len(russell_symbols),
        "symbols_with_usable_daily_history": len(rows),
        "symbols_missing_or_empty": len(missing),
        "sp500_symbol_overlap": sum(1 for row in rows if row["sp500_overlap"]),
        "latest_date_distribution": dict(sorted(latest_distribution.items())),
        "newest_local_daily_date": max(latest_distribution, default=""),
        "eligible_rows": rows,
        "missing_or_empty_symbols": missing,
        "limitations": [
            "Legacy membership list is not point-in-time Russell 2000 membership.",
            "This audit does not establish historical index membership, liquidity, delisting treatment, or tradability.",
            "Any future model must apply point-in-time eligibility, liquidity filters, higher small-cap costs, and chronological out-of-sample testing.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit legacy Russell daily coverage without changing data.")
    parser.add_argument("--daily-dir", type=Path, default=DEFAULT_DAILY_DIR)
    parser.add_argument("--russell-symbols", type=Path, default=DEFAULT_RUSSELL_SYMBOLS)
    parser.add_argument("--sp500-symbols", type=Path, default=DEFAULT_SP500_SYMBOLS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = audit_archive(args.daily_dir, load_symbols(args.russell_symbols), load_symbols(args.sp500_symbols))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "status", "russell_symbols_requested", "symbols_with_usable_daily_history",
        "symbols_missing_or_empty", "sp500_symbol_overlap", "newest_local_daily_date",
    )}, indent=2))


if __name__ == "__main__":
    main()
