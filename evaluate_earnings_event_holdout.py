from __future__ import annotations

"""Evaluate point-in-time earnings events on a later calendar-year holdout."""

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from alientai_v2.research.earnings_event_evaluator import select_event_rows, summarize


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate(rows: Sequence[Mapping[str, Any]], holdout_year: str, horizon_days: int, cost_pct: float) -> dict[str, Any]:
    # Identify visibility events against complete prior history, then filter.
    events = [row for row in select_event_rows(rows, horizon_days) if str(row.get("market_date") or "").startswith(holdout_year)]
    return {
        "status": "complete", "research_only": True, "execution_enabled": False,
        "warning": "Later-year earnings-event association only; events are not a standalone trading signal.",
        "holdout_year": holdout_year, "event_count": len(events), "horizon_trading_days": horizon_days,
        "round_trip_cost_pct": cost_pct, "buckets": summarize(events, cost_pct),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate earnings events on a later holdout year.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--holdout-year", required=True)
    parser.add_argument("--horizon-trading-days", type=int, default=5)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(read_jsonl(args.input), args.holdout_year, args.horizon_trading_days, args.round_trip_cost_pct)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
