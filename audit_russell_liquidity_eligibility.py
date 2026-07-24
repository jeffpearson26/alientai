from __future__ import annotations

"""Research-only point-in-time liquidity audit for legacy Russell candles.

The legacy archive is not a point-in-time index membership history.  This tool
does not treat it as one; it merely quantifies whether locally available rows
meet explicit price and rolling dollar-volume requirements before a future
small-cap experiment is proposed.
"""

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
DEFAULT_DAILY_DIR = ROOT / "data_v2" / "daily_schwab_max_history"
DEFAULT_SYMBOLS = DEFAULT_DAILY_DIR / "russell2000_symbols_used.txt"


def load_symbols(path: Path) -> list[str]:
    return sorted({line.strip().upper() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()})


def safe_float(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def read_candles(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle) if str(row.get("date") or "").strip()]
    return sorted(rows, key=lambda row: str(row.get("date") or ""))


def eligibility_counts(candles: Iterable[dict[str, Any]], *, min_price: float, min_avg_dollar_volume: float, lookback_days: int, max_calendar_gap_days: int = 5) -> dict[str, Any]:
    rows = list(candles)
    dollar_volumes = [safe_float(row.get("close")) * safe_float(row.get("volume")) for row in rows]
    dates = []
    for row in rows:
        try:
            dates.append(datetime.strptime(str(row.get("date") or ""), "%Y-%m-%d").date())
        except ValueError:
            dates.append(None)
    gap_prefix = [0] * len(rows)
    for idx in range(1, len(rows)):
        previous = dates[idx - 1]
        current = dates[idx]
        invalid_gap = previous is None or current is None or (current - previous).days <= 0 or (current - previous).days > max_calendar_gap_days
        gap_prefix[idx] = gap_prefix[idx - 1] + int(invalid_gap)
    eligible = 0
    checked = 0
    continuous_checked = 0
    extreme_five_day_returns = 0
    for idx, row in enumerate(rows):
        if idx < lookback_days - 1:
            continue
        checked += 1
        start_idx = idx - lookback_days + 1
        if gap_prefix[idx] != gap_prefix[start_idx]:
            continue
        continuous_checked += 1
        average_dollar_volume = sum(dollar_volumes[idx - lookback_days + 1:idx + 1]) / lookback_days
        if safe_float(row.get("close")) >= min_price and average_dollar_volume >= min_avg_dollar_volume:
            eligible += 1
        if idx + 5 < len(rows) and gap_prefix[idx + 5] == gap_prefix[idx]:
            current = safe_float(row.get("close"))
            future = safe_float(rows[idx + 5].get("close"))
            if current > 0 and future / current - 1 >= 1.0:
                extreme_five_day_returns += 1
    return {"rows": len(rows), "checked_rows": checked, "continuous_checked_rows": continuous_checked, "eligible_rows": eligible, "five_day_returns_over_100pct": extreme_five_day_returns}


def audit(daily_dir: Path, symbols: list[str], *, min_price: float, min_avg_dollar_volume: float, lookback_days: int, max_calendar_gap_days: int = 5) -> dict[str, Any]:
    summaries = []
    missing = []
    for symbol in symbols:
        path = daily_dir / f"{symbol.replace('/', '-').replace('.', '-')}_schwab_1d_max.csv"
        if not path.exists():
            missing.append(symbol)
            continue
        counts = eligibility_counts(read_candles(path), min_price=min_price, min_avg_dollar_volume=min_avg_dollar_volume, lookback_days=lookback_days, max_calendar_gap_days=max_calendar_gap_days)
        if not counts["rows"]:
            missing.append(symbol)
            continue
        summaries.append({"symbol": symbol, **counts})
    return {
        "status": "complete",
        "research_only": True,
        "policy": {"min_price": min_price, "min_avg_dollar_volume": min_avg_dollar_volume, "lookback_days": lookback_days, "max_calendar_gap_days": max_calendar_gap_days},
        "symbols_requested": len(symbols),
        "symbols_with_history": len(summaries),
        "symbols_missing_or_empty": len(missing),
        "rows_checked": sum(row["checked_rows"] for row in summaries),
        "continuous_rows_checked": sum(row["continuous_checked_rows"] for row in summaries),
        "rows_eligible": sum(row["eligible_rows"] for row in summaries),
        "five_day_returns_over_100pct": sum(row["five_day_returns_over_100pct"] for row in summaries),
        "symbol_summaries": summaries,
        "missing_or_empty_symbols": missing,
        "limitations": [
            "This is not point-in-time Russell 2000 membership.",
            "Passing this audit does not establish tradability, adjustment correctness, or predictive value.",
            "Thresholds are a pre-model data-quality screen, not a fitted trading rule.",
            "Five-session return counts require continuous forward daily history and are not model outcomes.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit local legacy Russell history with point-in-time liquidity screens.")
    parser.add_argument("--daily-dir", type=Path, default=DEFAULT_DAILY_DIR)
    parser.add_argument("--symbols-file", type=Path, default=DEFAULT_SYMBOLS)
    parser.add_argument("--min-price", type=float, default=5.0)
    parser.add_argument("--min-avg-dollar-volume", type=float, default=5_000_000.0)
    parser.add_argument("--lookback-days", type=int, default=20)
    parser.add_argument("--max-calendar-gap-days", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.min_price <= 0 or args.min_avg_dollar_volume <= 0 or args.lookback_days < 2 or args.max_calendar_gap_days < 1:
        raise ValueError("price, dollar volume, and lookback must be positive; lookback must be at least two days")
    report = audit(args.daily_dir, load_symbols(args.symbols_file), min_price=args.min_price, min_avg_dollar_volume=args.min_avg_dollar_volume, lookback_days=args.lookback_days, max_calendar_gap_days=args.max_calendar_gap_days)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "symbols_with_history", "rows_checked", "continuous_rows_checked", "rows_eligible", "five_day_returns_over_100pct")}, indent=2))


if __name__ == "__main__":
    main()
