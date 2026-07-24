from __future__ import annotations

"""Report extreme local legacy-Russell price moves for manual data-integrity review.

An extreme move is not automatically an error or a corporate action.  The
report deliberately preserves the row, dates, and unadjusted close values and
does not alter source candles or training labels.
"""

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
DEFAULT_DAILY_DIR = ROOT / "data_v2" / "daily_schwab_max_history"
DEFAULT_SYMBOLS = DEFAULT_DAILY_DIR / "russell2000_symbols_used.txt"


def safe_float(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def load_symbols(path: Path) -> list[str]:
    return sorted({line.strip().upper() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()})


def read_candles(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle) if str(row.get("date") or "").strip()]
    return sorted(rows, key=lambda row: str(row.get("date") or ""))


def find_discontinuities(symbol: str, candles: Iterable[dict[str, Any]], *, threshold_pct: float, horizon_days: int, max_calendar_gap_days: int = 5) -> tuple[list[dict[str, Any]], int]:
    rows = list(candles)
    dates = []
    for row in rows:
        try:
            dates.append(date.fromisoformat(str(row.get("date") or "")))
        except ValueError:
            dates.append(None)
    gap_prefix = [0] * len(rows)
    for idx in range(1, len(rows)):
        previous = dates[idx - 1]
        current = dates[idx]
        invalid_gap = previous is None or current is None or (current - previous).days <= 0 or (current - previous).days > max_calendar_gap_days
        gap_prefix[idx] = gap_prefix[idx - 1] + int(invalid_gap)
    findings = []
    skipped_discontinuous = 0
    for idx in range(len(rows) - horizon_days):
        if gap_prefix[idx + horizon_days] != gap_prefix[idx]:
            skipped_discontinuous += 1
            continue
        start = safe_float(rows[idx].get("close"))
        end = safe_float(rows[idx + horizon_days].get("close"))
        if start <= 0 or end <= 0:
            continue
        change_pct = (end / start - 1.0) * 100.0
        if abs(change_pct) >= threshold_pct:
            findings.append({
                "symbol": symbol,
                "horizon_trading_days": horizon_days,
                "start_date": str(rows[idx].get("date") or ""),
                "end_date": str(rows[idx + horizon_days].get("date") or ""),
                "start_close": start,
                "end_close": end,
                "change_pct": round(change_pct, 6),
            })
    return findings, skipped_discontinuous


def audit(daily_dir: Path, symbols: Iterable[str], *, threshold_pct: float, max_calendar_gap_days: int = 5) -> dict[str, Any]:
    one_day: list[dict[str, Any]] = []
    five_day: list[dict[str, Any]] = []
    missing = []
    skipped_discontinuous_windows = 0
    for symbol in symbols:
        path = daily_dir / f"{symbol.replace('/', '-').replace('.', '-')}_schwab_1d_max.csv"
        if not path.exists():
            missing.append(symbol)
            continue
        candles = read_candles(path)
        if not candles:
            missing.append(symbol)
            continue
        findings, skipped = find_discontinuities(symbol, candles, threshold_pct=threshold_pct, horizon_days=1, max_calendar_gap_days=max_calendar_gap_days)
        one_day.extend(findings)
        skipped_discontinuous_windows += skipped
        findings, skipped = find_discontinuities(symbol, candles, threshold_pct=threshold_pct, horizon_days=5, max_calendar_gap_days=max_calendar_gap_days)
        five_day.extend(findings)
        skipped_discontinuous_windows += skipped
    one_day.sort(key=lambda row: abs(float(row["change_pct"])), reverse=True)
    five_day.sort(key=lambda row: abs(float(row["change_pct"])), reverse=True)
    return {
        "status": "complete",
        "research_only": True,
        "threshold_pct": threshold_pct,
        "max_calendar_gap_days": max_calendar_gap_days,
        "symbols_missing_or_empty": len(missing),
        "discontinuous_windows_skipped": skipped_discontinuous_windows,
        "one_day_count": len(one_day),
        "five_day_count": len(five_day),
        "top_one_day_events": one_day[:100],
        "top_five_day_events": five_day[:100],
        "limitations": [
            "Extreme returns may be real market moves, splits, reverse splits, or data-quality issues.",
            "Windows with a date gap larger than the configured limit are excluded rather than treated as fixed-session returns.",
            "This report identifies rows for provenance/adjustment review; it does not classify or remove them.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only extreme-price-move audit for legacy Russell candles.")
    parser.add_argument("--daily-dir", type=Path, default=DEFAULT_DAILY_DIR)
    parser.add_argument("--symbols-file", type=Path, default=DEFAULT_SYMBOLS)
    parser.add_argument("--threshold-pct", type=float, default=50.0)
    parser.add_argument("--max-calendar-gap-days", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.threshold_pct <= 0 or args.max_calendar_gap_days < 1:
        raise ValueError("threshold-pct and max-calendar-gap-days must be positive")
    report = audit(args.daily_dir, load_symbols(args.symbols_file), threshold_pct=args.threshold_pct, max_calendar_gap_days=args.max_calendar_gap_days)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "one_day_count", "five_day_count", "discontinuous_windows_skipped", "symbols_missing_or_empty")}, indent=2))


if __name__ == "__main__":
    main()
