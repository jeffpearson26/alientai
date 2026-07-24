"""Build a research-only daily technical panel from local append-only Schwab CSVs."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from build_daily_technical_panel import snapshot_for_day, symbols


ROOT = Path(__file__).resolve().parent
DEFAULT_DAILY_DIR = ROOT / "data_v2" / "sp500_daily_schwab_max_history"


def csv_path(daily_dir: Path, symbol: str) -> Path:
    return daily_dir / f"{symbol.replace('/', '-').replace('.', '-')}_schwab_1d_max.csv"


def local_candles(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = []
        for row in csv.DictReader(handle):
            try:
                rows.append({"date": row["date"], "close": float(row["close"]), "high": float(row["high"]), "low": float(row["low"]), "volume": float(row["volume"])})
            except (KeyError, TypeError, ValueError):
                continue
        return rows


def build_panel(market_date: str, symbol_list: list[str], daily_dir: Path) -> tuple[list[dict], list[str]]:
    rows, missing = [], []
    for symbol in symbol_list:
        snapshot = snapshot_for_day(symbol, local_candles(csv_path(daily_dir, symbol)), market_date)
        if snapshot is None:
            missing.append(symbol)
        else:
            rows.append({"source": "schwab_local_daily_csv", **snapshot})
    return rows, missing


def main() -> None:
    parser = argparse.ArgumentParser(description="Build local Schwab daily technical panel for research only.")
    parser.add_argument("--market-date", required=True)
    parser.add_argument("--symbols-file", type=Path, default=DEFAULT_DAILY_DIR / "sp500_symbols_used.txt")
    parser.add_argument("--daily-dir", type=Path, default=DEFAULT_DAILY_DIR)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows, missing = build_panel(args.market_date, symbols(args.symbols_file), args.daily_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({"status": "complete", "research_only": True, "execution_enabled": False,
                      "source": "schwab_local_daily_csv", "market_date": args.market_date,
                      "rows": len(rows), "missing": len(missing)}, indent=2))


if __name__ == "__main__":
    main()
