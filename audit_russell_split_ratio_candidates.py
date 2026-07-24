from __future__ import annotations

"""Flag continuous one-session price jumps near common split ratios for review.

The source has no corporate-action confirmation field. A near 2x/3x/etc.
price ratio is only a review candidate and must never mutate candles, labels,
or eligibility without independently sourced corporate-action evidence.
"""

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from audit_russell_price_discontinuities import DEFAULT_DAILY_DIR, DEFAULT_SYMBOLS, load_symbols, read_candles, safe_float


def split_ratio_match(price_ratio: float, *, factors: tuple[int, ...], tolerance_pct: float) -> tuple[int, str] | None:
    if price_ratio <= 0:
        return None
    for factor in factors:
        if abs(price_ratio / factor - 1.0) <= tolerance_pct:
            return factor, "reverse_split_like"
        if abs(price_ratio * factor - 1.0) <= tolerance_pct:
            return factor, "split_like"
    return None


def find_candidates(symbol: str, candles: Iterable[dict[str, Any]], *, factors: tuple[int, ...], tolerance_pct: float, max_calendar_gap_days: int) -> tuple[list[dict[str, Any]], int]:
    rows = list(candles)
    candidates = []
    skipped_discontinuous = 0
    for idx in range(1, len(rows)):
        try:
            previous_date = date.fromisoformat(str(rows[idx - 1].get("date") or ""))
            current_date = date.fromisoformat(str(rows[idx].get("date") or ""))
        except ValueError:
            skipped_discontinuous += 1
            continue
        gap_days = (current_date - previous_date).days
        if gap_days <= 0 or gap_days > max_calendar_gap_days:
            skipped_discontinuous += 1
            continue
        previous_close = safe_float(rows[idx - 1].get("close"))
        current_close = safe_float(rows[idx].get("close"))
        if previous_close <= 0 or current_close <= 0:
            continue
        ratio = current_close / previous_close
        match = split_ratio_match(ratio, factors=factors, tolerance_pct=tolerance_pct)
        if not match:
            continue
        factor, direction = match
        candidates.append({
            "symbol": symbol,
            "previous_date": previous_date.isoformat(),
            "current_date": current_date.isoformat(),
            "previous_close": previous_close,
            "current_close": current_close,
            "price_ratio": round(ratio, 8),
            "candidate_factor": factor,
            "candidate_type": direction,
        })
    return candidates, skipped_discontinuous


def audit(daily_dir: Path, symbols: Iterable[str], *, factors: tuple[int, ...], tolerance_pct: float, max_calendar_gap_days: int) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    missing = []
    skipped_discontinuous = 0
    for symbol in sorted(set(symbols)):
        path = daily_dir / f"{symbol.replace('/', '-').replace('.', '-')}_schwab_1d_max.csv"
        if not path.exists():
            missing.append(symbol)
            continue
        rows = read_candles(path)
        if not rows:
            missing.append(symbol)
            continue
        found, skipped = find_candidates(symbol, rows, factors=factors, tolerance_pct=tolerance_pct, max_calendar_gap_days=max_calendar_gap_days)
        candidates.extend(found)
        skipped_discontinuous += skipped
    candidates.sort(key=lambda row: abs(float(row["price_ratio"]) - 1.0), reverse=True)
    by_factor = Counter(f"{row['candidate_factor']}:{row['candidate_type']}" for row in candidates)
    return {
        "status": "complete",
        "research_only": True,
        "factors": list(factors),
        "tolerance_pct": tolerance_pct,
        "max_calendar_gap_days": max_calendar_gap_days,
        "symbols_missing_or_empty": len(missing),
        "discontinuous_rows_skipped": skipped_discontinuous,
        "candidate_count": len(candidates),
        "candidate_symbols": sorted({str(row["symbol"]) for row in candidates}),
        "candidate_counts_by_factor_and_type": dict(sorted(by_factor.items())),
        "all_candidates": candidates,
        "top_candidates": candidates[:100],
        "limitations": [
            "A split-like price ratio is not confirmation of a split, reverse split, or bad data.",
            "No source rows, labels, eligibility decisions, or training inputs are modified by this report.",
            "Use an independent corporate-actions source before treating any candidate as an adjustment event.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only split-ratio candidate audit for legacy Russell candles.")
    parser.add_argument("--daily-dir", type=Path, default=DEFAULT_DAILY_DIR)
    parser.add_argument("--symbols-file", type=Path, default=DEFAULT_SYMBOLS)
    parser.add_argument("--tolerance-pct", type=float, default=0.03)
    parser.add_argument("--max-calendar-gap-days", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.tolerance_pct <= 0 or args.max_calendar_gap_days < 1:
        raise ValueError("tolerance-pct and max-calendar-gap-days must be positive")
    report = audit(args.daily_dir, load_symbols(args.symbols_file), factors=(2, 3, 4, 5, 10), tolerance_pct=args.tolerance_pct, max_calendar_gap_days=args.max_calendar_gap_days)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "candidate_count", "candidate_counts_by_factor_and_type", "discontinuous_rows_skipped")}, indent=2))


if __name__ == "__main__":
    main()
