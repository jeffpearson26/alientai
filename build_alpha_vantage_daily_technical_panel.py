"""Build a same-source technical panel from compact Alpha Vantage daily files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_daily_technical_panel import snapshot_for_day, symbols


def candles(path: Path) -> list[dict]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    series = next((value for key, value in payload.items() if str(key).startswith("Time Series")), {})
    return [
        {
            "date": day,
            "open": values.get("1. open"),
            "high": values.get("2. high"),
            "low": values.get("3. low"),
            "close": values.get("4. close"),
            "volume": values.get("5. volume"),
        }
        for day, values in series.items()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an Alpha Vantage compact-daily technical panel.")
    parser.add_argument("--market-date", required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows, missing = [], []
    for symbol in symbols(args.symbols_file):
        filename = f"{symbol.replace('/', '-').replace('.', '-')}_daily.json"
        snapshot = snapshot_for_day(symbol, candles(args.daily_dir / filename), args.market_date)
        if snapshot is None:
            missing.append(symbol)
        else:
            rows.append({"source": "alpha_vantage_time_series_daily", **snapshot})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({"status": "complete", "market_date": args.market_date,
                      "rows": len(rows), "missing": len(missing)}, indent=2))


if __name__ == "__main__":
    main()
