from __future__ import annotations

"""Collect a bounded symbol/date options panel using the shared safe archiver."""

import argparse
import os
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

from download_alpha_vantage_historical_options import ROOT, run


def read_symbols(path: Path) -> list[str]:
    symbols = []
    for line in path.read_text(encoding="utf-8").splitlines():
        symbol = line.strip().upper()
        if symbol and not symbol.startswith("#"):
            symbols.append(symbol)
    return list(dict.fromkeys(symbols))


def market_weekdays(start_date: str, end_date: str) -> list[str]:
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    if end < start:
        raise ValueError("end_date must not precede start_date")
    days = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def panel_requests(symbols: list[str], start_date: str, end_date: str) -> list[tuple[str, str]]:
    return [(symbol, day) for day in market_weekdays(start_date, end_date) for symbol in symbols]


def main() -> None:
    parser = argparse.ArgumentParser(description="Resumable Alpha Vantage options-panel collector.")
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--delay-seconds", type=float, default=0.25)
    parser.add_argument("--limit-requests", type=int, default=0)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    items = panel_requests(read_symbols(args.symbols_file), args.start_date, args.end_date)
    if args.limit_requests:
        items = items[:args.limit_requests]
    result = run(items, api_key, args.output, args.delay_seconds)
    print({"status": result["status"], "requests": len(items), "completed": len(result["completed"]), "unavailable": len(result["unavailable"])})


if __name__ == "__main__":
    main()
