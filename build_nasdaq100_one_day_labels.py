from __future__ import annotations

"""Attach executable next-session open-to-close labels to Nasdaq training rows."""

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any


TARGET = "label_next_session_open_to_close_return_pct"


def target_name(horizon_sessions: int) -> str:
    if horizon_sessions < 1:
        raise ValueError("horizon_sessions must be positive")
    return TARGET if horizon_sessions == 1 else f"label_{horizon_sessions}_session_open_to_close_return_pct"


def load_daily(directory: Path) -> dict[str, list[dict[str, Any]]]:
    output = {}
    for path in directory.glob("*_schwab_1d_max.csv"):
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = []
            for row in csv.DictReader(handle):
                try:
                    rows.append({
                        "date": date.fromisoformat(row["date"]),
                        "open": float(row["open"]),
                        "close": float(row["close"]),
                    })
                except (KeyError, TypeError, ValueError):
                    continue
        if rows:
            output[path.name.removesuffix("_schwab_1d_max.csv").upper()] = sorted(rows, key=lambda row: row["date"])
    return output


def attach_labels(
    rows: list[dict[str, Any]],
    daily: dict[str, list[dict[str, Any]]],
    horizon_sessions: int = 1,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    target = target_name(horizon_sessions)
    output, counts = [], {"input_rows": len(rows), "labeled_rows": 0, "missing_symbol": 0, "missing_anchor": 0, "missing_next_session": 0}
    indexed = {}
    for symbol, candles in daily.items():
        indexed[symbol] = {row["date"]: index for index, row in enumerate(candles)}
    for row in rows:
        symbol = str(row.get("symbol") or "").upper()
        candles = daily.get(symbol)
        if not candles:
            counts["missing_symbol"] += 1
            continue
        try:
            nominal = date.fromisoformat(str(row["market_date"]))
            expected_close = float(row["close"])
        except (KeyError, TypeError, ValueError):
            counts["missing_anchor"] += 1
            continue
        anchors = [
            (index, candle) for index, candle in enumerate(candles)
            if abs((candle["date"] - nominal).days) <= 3
            and abs(candle["close"] / expected_close - 1.0) <= 0.00001
        ]
        if not anchors:
            counts["missing_anchor"] += 1
            continue
        index, anchor = min(anchors, key=lambda item: (abs((item[1]["date"] - nominal).days), item[1]["date"]))
        if index + horizon_sessions >= len(candles):
            counts["missing_next_session"] += 1
            continue
        entry = candles[index + 1]
        future = candles[index + horizon_sessions]
        if (
            entry["open"] <= 0 or future["close"] <= 0
            or (future["date"] - anchor["date"]).days > horizon_sessions * 3 + 3
        ):
            counts["missing_next_session"] += 1
            continue
        output.append({
            **row,
            "label_horizon_sessions": horizon_sessions,
            "label_entry_market_date": entry["date"].isoformat(),
            "label_entry_open": entry["open"],
            "label_exit_market_date": future["date"].isoformat(),
            "label_exit_close": future["close"],
            target: (future["close"] / entry["open"] - 1.0) * 100.0,
        })
        counts["labeled_rows"] += 1
    return output, counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--horizon-sessions", type=int, default=1)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    target = target_name(args.horizon_sessions)
    labeled, counts = attach_labels(rows, load_daily(args.daily_dir), args.horizon_sessions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in labeled:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    args.summary.write_text(json.dumps({
        "status": "complete", "target": target,
        "horizon_sessions": args.horizon_sessions, **counts,
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
