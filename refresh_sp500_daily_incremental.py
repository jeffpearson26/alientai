"""Append recent Schwab daily candles without rewriting historical local rows.

This is research-data maintenance only.  It neither uploads to Supabase nor
starts a trainer, engine, paper account, or live order path.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any

from download_sp500_daily_schwab_max import (
    OUT_DIR, PROJECT_ROOT, candle_date, candle_datetime, schwab_get_json,
    schwab_symbol_variants,
)


FIELDS = ("symbol", "schwab_symbol", "date", "datetime", "open", "high", "low", "close", "volume")


def read_symbols(path: Path) -> list[str]:
    return list(dict.fromkeys(
        line.split(",", 1)[0].strip().upper()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ))


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def append_only(existing: list[dict[str, str]], recent: list[dict[str, str]]) -> list[dict[str, str]]:
    newest = max((str(row.get("date") or "") for row in existing), default="")
    additions = [row for row in recent if str(row.get("date") or "") > newest]
    return existing + sorted(additions, key=lambda row: str(row.get("date") or ""))


def fetch_recent(symbol: str) -> tuple[str, list[dict[str, Any]]]:
    last_error: Exception | None = None
    for variant in schwab_symbol_variants(symbol):
        try:
            payload = schwab_get_json("https://api.schwabapi.com/marketdata/v1/pricehistory", {
                "symbol": variant, "periodType": "month", "period": 1,
                "frequencyType": "daily", "frequency": 1,
                "needExtendedHoursData": "false",
            })
            candles = payload.get("candles") or []
            if candles:
                return variant, candles
            last_error = RuntimeError(f"no daily candles returned for {variant}")
        except Exception as exc:
            last_error = exc
    raise RuntimeError(str(last_error or f"no daily candles returned for {symbol}"))


def normalize(symbol: str, schwab_symbol: str, candles: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [{
        "symbol": symbol, "schwab_symbol": schwab_symbol,
        "date": candle_date(candle.get("datetime")), "datetime": candle_datetime(candle.get("datetime")),
        "open": str(candle.get("open") or ""), "high": str(candle.get("high") or ""),
        "low": str(candle.get("low") or ""), "close": str(candle.get("close") or ""),
        "volume": str(candle.get("volume") or ""),
    } for candle in candles if candle_date(candle.get("datetime"))]


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Append only newer S&P daily candles from Schwab.")
    parser.add_argument("--symbols-file", type=Path, default=OUT_DIR / "sp500_symbols_used.txt")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--delay", type=float, default=0.20)
    parser.add_argument("--max-symbols", type=int, default=0)
    parser.add_argument("--apply", action="store_true", help="Write new rows; without this, perform a remote dry run.")
    args = parser.parse_args()
    symbols = read_symbols(args.symbols_file)
    if args.max_symbols:
        symbols = symbols[:args.max_symbols]
    results, failures, additions = [], {}, 0
    for index, symbol in enumerate(symbols, start=1):
        path = args.output_dir / f"{symbol.replace('/', '-').replace('.', '-')}_schwab_1d_max.csv"
        try:
            existing = read_existing(path)
            schwab_symbol, candles = fetch_recent(symbol)
            merged = append_only(existing, normalize(symbol, schwab_symbol, candles))
            added = len(merged) - len(existing)
            if args.apply and added:
                write_rows(path, merged)
            additions += added
            results.append({"symbol": symbol, "existing_rows": len(existing), "new_rows": added,
                            "latest_date": max((row.get("date") or "" for row in merged), default="")})
            print(f"[{index}/{len(symbols)}] {symbol}: +{added}", flush=True)
        except Exception as exc:
            failures[symbol] = str(exc)
            print(f"[{index}/{len(symbols)}] {symbol}: ERROR {exc}", flush=True)
            if "401 unauthorized" in str(exc).lower():
                print("STOPPING: Schwab token must be refreshed before another incremental request.", flush=True)
                break
        if args.delay > 0:
            time.sleep(args.delay)
    report = {"status": "complete", "research_only": True, "execution_enabled": False,
              "apply": args.apply, "symbols": len(symbols), "new_rows": additions,
              "failures": failures, "results": results}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "sp500_daily_incremental_refresh_summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "apply", "symbols", "new_rows", "failures")}, indent=2))


if __name__ == "__main__":
    main()
