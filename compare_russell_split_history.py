from __future__ import annotations

"""Compare split-ratio review flags with archived provider split events.

This is a reconciliation report, not a price-adjustment process. It retains
unmatched events and makes no change to candle files, labels, models, or
eligibility rules.
"""

import argparse
import gzip
import json
from datetime import date
from pathlib import Path
from typing import Any


def load_candidates(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    candidates = payload.get("all_candidates")
    if not isinstance(candidates, list):
        raise ValueError("candidate report lacks all_candidates")
    return [row for row in candidates if isinstance(row, dict)]


def load_events(splits_dir: Path) -> dict[str, list[dict[str, Any]]]:
    events: dict[str, list[dict[str, Any]]] = {}
    for path in splits_dir.glob("*.json.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            document = json.load(handle)
        symbol = str(document.get("symbol") or "").upper()
        payload = document.get("payload") or {}
        rows = payload.get("data") if isinstance(payload, dict) else []
        if symbol and isinstance(rows, list):
            events[symbol] = [row for row in rows if isinstance(row, dict)]
    return events


def reconcile(candidates: list[dict[str, Any]], events_by_symbol: dict[str, list[dict[str, Any]]], *, date_tolerance_days: int, ratio_tolerance_pct: float) -> dict[str, Any]:
    results = []
    counts = {"date_and_ratio_match": 0, "date_only_match": 0, "unmatched": 0, "missing_provider_symbol": 0}
    for candidate in candidates:
        symbol = str(candidate.get("symbol") or "").upper()
        try:
            candidate_date = date.fromisoformat(str(candidate.get("current_date") or ""))
            candidate_ratio = float(candidate.get("price_ratio"))
        except (TypeError, ValueError):
            continue
        provider_rows = events_by_symbol.get(symbol)
        if provider_rows is None:
            status = "missing_provider_symbol"
            matches: list[dict[str, Any]] = []
        else:
            matches = []
            for event in provider_rows:
                try:
                    event_date = date.fromisoformat(str(event.get("effective_date") or ""))
                    split_factor = float(event.get("split_factor"))
                except (TypeError, ValueError):
                    continue
                if abs((event_date - candidate_date).days) <= date_tolerance_days:
                    matches.append({"effective_date": event_date.isoformat(), "split_factor": split_factor})
            ratio_match = any(split_factor > 0 and abs(candidate_ratio / split_factor - 1.0) <= ratio_tolerance_pct for match in matches for split_factor in [float(match["split_factor"])])
            status = "date_and_ratio_match" if ratio_match else ("date_only_match" if matches else "unmatched")
        counts[status] += 1
        results.append({**candidate, "provider_match_status": status, "provider_nearby_events": matches})
    return {
        "status": "complete",
        "research_only": True,
        "candidate_count": len(results),
        "provider_symbols_loaded": len(events_by_symbol),
        "date_tolerance_days": date_tolerance_days,
        "ratio_tolerance_pct": ratio_tolerance_pct,
        "counts": counts,
        "results": results,
        "limitations": [
            "A provider date/factor match supports review of a possible corporate action; it does not itself authorize a price rewrite.",
            "Unmatched events may be genuine market moves, incomplete provider coverage, timing differences, or data-quality issues.",
            "This report has no training, scoring, broker, settings, or source-candle write path.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile Russell split-ratio candidates against archived split history.")
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--splits-dir", type=Path, required=True)
    parser.add_argument("--date-tolerance-days", type=int, default=3)
    parser.add_argument("--ratio-tolerance-pct", type=float, default=0.10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.date_tolerance_days < 0 or args.ratio_tolerance_pct <= 0:
        raise ValueError("date tolerance must be non-negative and ratio tolerance must be positive")
    report = reconcile(load_candidates(args.candidates), load_events(args.splits_dir), date_tolerance_days=args.date_tolerance_days, ratio_tolerance_pct=args.ratio_tolerance_pct)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "candidate_count", "provider_symbols_loaded", "counts")}, indent=2))


if __name__ == "__main__":
    main()
