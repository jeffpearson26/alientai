"""Fail-closed alignment audit for separately archived daily price sources."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
from typing import Any, Mapping


def schwab_closes(path: Path) -> dict[str, float]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {str(row["date"]): float(row["close"]) for row in csv.DictReader(handle) if row.get("date") and row.get("close")}


def alpha_closes(path: Path) -> dict[str, float]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    series = next((value for key, value in payload.items() if str(key).startswith("Time Series")), None)
    if not isinstance(series, Mapping):
        return {}
    return {str(day): float(value["4. close"]) for day, value in series.items() if isinstance(value, Mapping) and value.get("4. close")}


def audit_symbol(symbol: str, alpha: Mapping[str, float], schwab: Mapping[str, float], tolerance: float) -> dict[str, Any]:
    same, previous, mismatched = 0, 0, 0
    comparisons = []
    ordered_schwab_dates = sorted(schwab)
    for day in sorted(set(alpha) & set(schwab)):
        alpha_close, same_close = alpha[day], schwab[day]
        prior = max((date for date in ordered_schwab_dates if date < day), default=None)
        prior_close = schwab.get(prior or "")
        same_match = abs(alpha_close - same_close) <= tolerance
        prior_match = prior_close is not None and abs(alpha_close - prior_close) <= tolerance
        same += int(same_match)
        previous += int(prior_match)
        mismatched += int(not same_match)
        comparisons.append({"date": day, "same_day_match": same_match, "prior_session_match": prior_match})
    return {"symbol": symbol, "overlapping_dates": len(comparisons), "same_day_matches": same,
            "prior_session_matches": previous, "same_day_mismatches": mismatched, "comparisons": comparisons}


def audit(symbols: list[str], alpha_dir: Path, schwab_dir: Path, tolerance: float = 0.01) -> dict[str, Any]:
    rows = []
    for symbol in symbols:
        alpha_path = alpha_dir / f"{symbol}_daily.json.gz"
        schwab_path = schwab_dir / f"{symbol}_schwab_1d_max.csv"
        if not alpha_path.exists() or not schwab_path.exists():
            rows.append({"symbol": symbol, "missing_source": True})
            continue
        rows.append(audit_symbol(symbol, alpha_closes(alpha_path), schwab_closes(schwab_path), tolerance))
    mismatches = sum(int(row.get("same_day_mismatches") or 0) for row in rows)
    return {"status": "complete", "research_only": True, "execution_enabled": False,
            "source_mixing_authorized": False, "same_day_alignment_passes": mismatches == 0,
            "symbols": rows, "warning": "A failed audit means Alpha Vantage data cannot be used as a same-day outcome fallback."}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Alpha Vantage and Schwab daily source date alignment.")
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--alpha-dir", type=Path, required=True)
    parser.add_argument("--schwab-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    if payload.get("research_only") is not True or payload.get("execution_enabled") is not False:
        raise ValueError("payload must be explicitly research-only and execution-disabled")
    symbols = list(dict.fromkeys(str(item.get("symbol") or "").upper() for item in payload.get("candidates") or [] if item.get("symbol")))
    result = audit(symbols, args.alpha_dir, args.schwab_dir)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "same_day_alignment_passes", "source_mixing_authorized")}, indent=2))


if __name__ == "__main__":
    main()
