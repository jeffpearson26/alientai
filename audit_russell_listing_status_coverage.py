from __future__ import annotations

"""Audit legacy-symbol presence in dated active-listing snapshots.

Active listing presence is a survivorship reference check only. It does not
establish historical Russell 2000 membership, liquidity, or tradability.
"""

import argparse
import csv
import gzip
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_RUSSELL = ROOT / "data_v2" / "daily_schwab_max_history" / "russell2000_symbols_used.txt"
DEFAULT_SP500 = ROOT / "data_v2" / "sp500_daily_schwab_max_history" / "sp500_symbols_used.txt"


def load_symbols(path: Path) -> set[str]:
    return {line.strip().upper() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip() and not line.lstrip().startswith("#")}


def snapshot_date(path: Path) -> str:
    match = re.fullmatch(r"listing_status_active_(\d{4}-\d{2}-\d{2})\.csv\.gz", path.name)
    if not match:
        raise ValueError(f"unexpected listing-status filename: {path.name}")
    return match.group(1)


def active_stock_symbols(path: Path) -> set[str]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return {
            str(row.get("symbol") or "").strip().upper()
            for row in csv.DictReader(handle)
            if str(row.get("symbol") or "").strip()
            and str(row.get("assetType") or "").strip().casefold() == "stock"
            and str(row.get("status") or "").strip().casefold() == "active"
        }


def audit(snapshot_dir: Path, russell_symbols: set[str], sp500_symbols: set[str]) -> dict[str, Any]:
    rows = []
    for path in sorted(snapshot_dir.glob("listing_status_active_*.csv.gz")):
        active = active_stock_symbols(path)
        legacy_active = russell_symbols & active
        rows.append({
            "snapshot_date": snapshot_date(path),
            "active_us_stock_count": len(active),
            "legacy_symbols_present_as_active_stocks": len(legacy_active),
            "legacy_symbols_absent_from_active_snapshot": len(russell_symbols - legacy_active),
            "legacy_active_current_sp500_overlap": len(legacy_active & sp500_symbols),
        })
    if not rows:
        raise ValueError("no listing_status_active_YYYY-MM-DD.csv.gz files found")
    return {
        "status": "complete",
        "research_only": True,
        "legacy_symbol_count": len(russell_symbols),
        "current_sp500_symbol_count": len(sp500_symbols),
        "snapshots": rows,
        "limitations": [
            "Active-listing presence is not Russell 2000 membership or point-in-time index composition.",
            "Current S&P overlap is a contamination warning, not historical S&P membership.",
            "This report does not establish liquidity, corporate-action correctness, or model eligibility.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only legacy Russell active-listing coverage audit.")
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--russell-symbols", type=Path, default=DEFAULT_RUSSELL)
    parser.add_argument("--sp500-symbols", type=Path, default=DEFAULT_SP500)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.snapshot_dir, load_symbols(args.russell_symbols), load_symbols(args.sp500_symbols))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "snapshots": len(report["snapshots"]), "first": report["snapshots"][0], "last": report["snapshots"][-1]}, indent=2))


if __name__ == "__main__":
    main()
