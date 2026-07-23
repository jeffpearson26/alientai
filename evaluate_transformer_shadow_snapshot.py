from __future__ import annotations

"""Evaluate completed Transformer shadow records from local daily candles only."""

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def candles(path: Path) -> list[dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def completed_return(rows: Sequence[Mapping[str, Any]], as_of_date: str, horizon_days: int) -> float | None:
    dates = [str(row.get("date") or "") for row in rows]
    if as_of_date not in dates:
        return None
    entry_index = dates.index(as_of_date)
    exit_index = entry_index + horizon_days
    if exit_index >= len(rows):
        return None
    entry = float(rows[entry_index].get("close") or 0)
    exit_ = float(rows[exit_index].get("close") or 0)
    if entry <= 0 or exit_ <= 0:
        return None
    return (exit_ / entry - 1.0) * 100.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate mature non-executing Transformer shadow records.")
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--review-date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    review_day = date.fromisoformat(args.review_date)
    pending, completed = [], []
    for item in read_jsonl(args.journal):
        if review_day < date.fromisoformat(str(item["outcome_not_due_before"])):
            pending.append(item)
            continue
        symbol = str(item["symbol"])
        value = completed_return(candles(args.daily_dir / f"{symbol}_schwab_1d_max.csv"), str(item["as_of_date"]), int(item["horizon_calendar_days"]))
        if value is None:
            pending.append({**item, "outcome_status": "PENDING_CANDLE_COVERAGE"})
        else:
            completed.append({**item, "realized_return_pct": value, "outcome_status": "COMPLETE"})
    report = {
        "status": "complete", "research_only": True, "execution_enabled": False,
        "review_date": args.review_date, "completed": len(completed), "pending": len(pending),
        "mean_realized_return_pct": sum(item["realized_return_pct"] for item in completed) / len(completed) if completed else None,
        "records": completed, "pending_records": pending,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in {"records", "pending_records"}}, indent=2))


if __name__ == "__main__":
    main()
