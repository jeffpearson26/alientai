from __future__ import annotations

"""Build source-consistent technical/label rows from local Schwab daily CSVs."""

import argparse
import csv
import json
from datetime import date
from pathlib import Path

from alientai_v2.features.technical_snapshot import build_technical_snapshot


def symbols(path: Path) -> list[str]:
    return [
        line.strip().upper() for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def build_rows(
    candles: list[dict],
    symbol: str,
    start: date,
    end: date,
    horizon_sessions: int = 5,
    benchmark_candles: list[dict] | None = None,
    benchmark_symbol: str | None = None,
) -> list[dict]:
    benchmark_by_date = {
        row["date"]: index for index, row in enumerate(benchmark_candles or [])
    }
    output = []
    for index in range(59, len(candles) - horizon_sessions):
        current = candles[index]
        current_day = date.fromisoformat(current["date"])
        if not start <= current_day <= end:
            continue
        close = float(current["close"])
        future = candles[index + horizon_sessions]
        row = {
            "symbol": symbol,
            "market_date": current["date"],
            "future_market_date": future["date"],
            "close": close,
            "label_forward_return_5d_pct": (float(future["close"]) / close - 1.0) * 100.0,
            **build_technical_snapshot(candles[index - 59:index + 1]),
        }
        if benchmark_candles is not None and benchmark_symbol:
            benchmark_index = benchmark_by_date.get(current["date"])
            if benchmark_index is None or benchmark_index < 60:
                continue
            benchmark_close = float(benchmark_candles[benchmark_index]["close"])
            row["benchmark_symbol"] = benchmark_symbol
            for lookback in (5, 20, 60):
                stock_return = (
                    close / float(candles[index - lookback]["close"]) - 1.0
                ) * 100.0
                benchmark_return = (
                    benchmark_close
                    / float(benchmark_candles[benchmark_index - lookback]["close"])
                    - 1.0
                ) * 100.0
                row[f"technical_benchmark_return_{lookback}d_pct"] = benchmark_return
                row[f"technical_relative_return_{lookback}d_pct"] = (
                    stock_return - benchmark_return
                )
        output.append(row)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--benchmark-symbol")
    args = parser.parse_args()
    benchmark_candles = None
    benchmark_symbol = (args.benchmark_symbol or "").strip().upper() or None
    if benchmark_symbol:
        benchmark_path = args.daily_dir / f"{benchmark_symbol}_schwab_1d_max.csv"
        if not benchmark_path.exists():
            raise SystemExit(f"missing benchmark history: {benchmark_path}")
        with benchmark_path.open("r", encoding="utf-8", newline="") as handle:
            benchmark_candles = [row for row in csv.DictReader(handle)]
    all_rows, coverage = [], []
    for symbol in symbols(args.symbols_file):
        path = args.daily_dir / f"{symbol}_schwab_1d_max.csv"
        if not path.exists():
            coverage.append({"symbol": symbol, "rows": 0, "status": "missing"})
            continue
        with path.open("r", encoding="utf-8", newline="") as handle:
            candles = [row for row in csv.DictReader(handle)]
        rows = build_rows(
            candles,
            symbol,
            args.start_date,
            args.end_date,
            benchmark_candles=benchmark_candles,
            benchmark_symbol=benchmark_symbol,
        )
        all_rows.extend(rows)
        coverage.append({
            "symbol": symbol, "rows": len(rows),
            "status": "complete" if rows else "insufficient_history",
        })
    all_rows.sort(key=lambda row: (row["market_date"], row["symbol"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in all_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    summary = {
        "status": "complete",
        "source": "local_schwab_daily_csv",
        "benchmark_symbol": benchmark_symbol,
        "start_date": args.start_date.isoformat(),
        "end_date": args.end_date.isoformat(),
        "symbols_requested": len(coverage),
        "symbols_with_rows": sum(row["rows"] > 0 for row in coverage),
        "rows": len(all_rows),
        "coverage": coverage,
    }
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
