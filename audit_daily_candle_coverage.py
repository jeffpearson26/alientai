from __future__ import annotations

"""Audit latest daily-candle availability without changing market data or trading state."""

import argparse
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from alientai_v2.history.supabase_candle_reader import fetch_symbol_candles


ROOT = Path(__file__).resolve().parent


def read_symbols(path: Path) -> list[str]:
    symbols: list[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        symbol = line.split(",", 1)[0].strip().upper()
        if symbol and not symbol.startswith("#") and symbol not in symbols:
            symbols.append(symbol)
    return symbols


def latest_day(rows: Iterable[Mapping[str, Any]]) -> str | None:
    values: list[str] = []
    for row in rows:
        value = str(row.get("datetime_utc") or "")[:10]
        if len(value) != 10:
            continue
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            continue
        values.append(value)
    return max(values, default=None)


def summarize_latest_days(latest_by_symbol: Mapping[str, str | None]) -> dict[str, Any]:
    available = {symbol: day for symbol, day in latest_by_symbol.items() if day}
    counts = Counter(available.values())
    newest = max(counts, default=None)
    return {
        "symbols_requested": len(latest_by_symbol),
        "symbols_with_daily_history": len(available),
        "symbols_without_daily_history": sorted(symbol for symbol, day in latest_by_symbol.items() if not day),
        "newest_available_market_date": newest,
        "symbols_at_newest_date": counts.get(newest, 0) if newest else 0,
        "latest_date_distribution": dict(sorted(counts.items())),
        "symbols_by_latest_date": dict(sorted(available.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only daily-candle coverage audit.")
    parser.add_argument("--symbols-file", type=Path, default=ROOT / "sp500_expanded_symbols.txt")
    parser.add_argument("--table", default="v2_daily_candles")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--delay-seconds", type=float, default=0.05)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.limit <= 0 or args.delay_seconds < 0:
        raise ValueError("limit must be positive and delay-seconds cannot be negative")

    latest_by_symbol: dict[str, str | None] = {}
    failures: dict[str, str] = {}
    symbols = read_symbols(args.symbols_file)
    for index, symbol in enumerate(symbols, 1):
        try:
            latest_by_symbol[symbol] = latest_day(
                fetch_symbol_candles(symbol, table=args.table, limit=args.limit)
            )
        except Exception as exc:  # Record coverage failure; do not classify it as no history.
            failures[symbol] = type(exc).__name__
            latest_by_symbol[symbol] = None
        print(f"[{index}/{len(symbols)}] {symbol}: {latest_by_symbol[symbol] or 'missing'}")
        if args.delay_seconds:
            time.sleep(args.delay_seconds)

    report = {
        "status": "complete",
        "research_only": True,
        "table": args.table,
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "fetch_failures": failures,
        **summarize_latest_days(latest_by_symbol),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "symbols_requested": report["symbols_requested"],
        "symbols_with_daily_history": report["symbols_with_daily_history"],
        "newest_available_market_date": report["newest_available_market_date"],
        "symbols_at_newest_date": report["symbols_at_newest_date"],
        "fetch_failures": len(failures),
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
