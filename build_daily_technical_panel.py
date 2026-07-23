from __future__ import annotations

"""Build one research-only technical snapshot per symbol for one market date."""

import argparse
import json
from pathlib import Path

from alientai_v2.features.technical_snapshot import build_technical_snapshot
from alientai_v2.history.supabase_candle_reader import fetch_symbol_candles
from alientai_v2.research.rcef_rows import canonical_candles, candle_date


ROOT = Path(__file__).resolve().parent


def symbols(path: Path) -> list[str]:
    output = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        value = line.split(",", 1)[0].strip().upper()
        if value and not value.startswith("#") and value not in output:
            output.append(value)
    return output


def snapshot_for_day(symbol: str, rows: list[dict], market_date: str) -> dict | None:
    candles = canonical_candles(rows)
    matching = [index for index, row in enumerate(candles) if candle_date(row).isoformat() == market_date]
    if not matching:
        return None
    index = matching[-1]
    if index < 59:
        return None
    current = candles[index]
    return {"symbol": symbol, "market_date": market_date, "close": float(current["close"]), **build_technical_snapshot(candles[index - 59:index + 1])}


def main() -> None:
    parser = argparse.ArgumentParser(description="Research-only daily technical panel builder.")
    parser.add_argument("--market-date", required=True)
    parser.add_argument("--symbols-file", type=Path, default=ROOT / "sp500_expanded_symbols.txt")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = []
    missing = []
    for index, symbol in enumerate(symbols(args.symbols_file), 1):
        row = snapshot_for_day(symbol, fetch_symbol_candles(symbol, table="v2_daily_candles", limit=1000), args.market_date)
        if row is None:
            missing.append(symbol)
        else:
            result.append(row)
        print(f"[{index}] {symbol}: {'ok' if row else 'missing'}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in result:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({"status":"complete","research_only":True,"market_date":args.market_date,"rows":len(result),"missing":len(missing),"execution_enabled":False}, indent=2))


if __name__ == "__main__":
    main()
