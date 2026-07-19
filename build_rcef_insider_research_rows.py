from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from supabase import create_client

from alientai_v2.history.supabase_candle_reader import fetch_symbol_candles
from alientai_v2.research.rcef_rows import build_research_rows
from alientai_v2.features.earnings_features import fetch_symbol_earnings


ROOT = Path(__file__).resolve().parent


def symbols(path: Path, limit: int) -> List[str]:
    values = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        symbol = line.split(",", 1)[0].strip().upper()
        if symbol and not symbol.startswith("#") and symbol not in values:
            values.append(symbol)
        if limit and len(values) >= limit:
            break
    return values


def fetch_purchases(client: Any, symbol: str) -> List[Dict[str, Any]]:
    response = (
        client.table("v2_sec_form4_purchases").select("*")
        .eq("ticker", symbol).eq("is_training_eligible", True)
        .order("available_at_utc").limit(5000).execute()
    )
    return list(response.data or [])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols-file", type=Path, default=ROOT / "sp500_expanded_symbols.txt")
    parser.add_argument("--limit-symbols", type=int, default=5)
    parser.add_argument("--candle-limit", type=int, default=10000)
    parser.add_argument("--output", type=Path, default=ROOT / "data_v2" / "rcef_research" / "insider_pilot_rows.jsonl")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    benchmark = fetch_symbol_candles("SPY", table="v2_daily_candles", limit=args.candle_limit)
    output: List[Dict[str, Any]] = []
    for index, symbol in enumerate(symbols(args.symbols_file, args.limit_symbols), 1):
        print(f"[{index}] {symbol}")
        candles = fetch_symbol_candles(symbol, table="v2_daily_candles", limit=args.candle_limit)
        purchases = fetch_purchases(client, symbol)
        earnings = fetch_symbol_earnings(client, symbol)
        rows = build_research_rows(
            symbol=symbol, candles=candles, benchmark_candles=benchmark,
            sec_purchases=purchases,
            earnings_events=earnings,
        )
        print(f"  candles={len(candles)} purchases={len(purchases)} earnings={len(earnings)} rows={len(rows)}")
        output.extend(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in output:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    summary = {
        "symbols": len({row["symbol"] for row in output}), "rows": len(output),
        "rows_with_visible_purchase": sum(bool(row["insider_purchase_available"]) for row in output),
        "output": str(args.output),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
