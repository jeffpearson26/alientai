"""Prepare a deterministic, time-stratified natural-universe news sample."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def select_dates(rows: Iterable[dict[str, Any]], date_count: int, minimum_rows_per_date: int) -> list[str]:
    counts = Counter(str(row.get("market_date") or "") for row in rows)
    eligible = sorted(day for day, count in counts.items() if day and count >= minimum_rows_per_date)
    if date_count < 3:
        raise ValueError("date_count must be at least three")
    if len(eligible) < date_count:
        raise ValueError("not enough complete market dates for requested stratified sample")
    # Endpoints are included; each interior position uses a fixed rounded index.
    indexes = [round(index * (len(eligible) - 1) / (date_count - 1)) for index in range(date_count)]
    selected = [eligible[index] for index in indexes]
    if len(set(selected)) != date_count:
        raise ValueError("stratified date selection produced duplicates")
    return selected


def select_rows(rows: Iterable[dict[str, Any]], dates: Iterable[str]) -> list[dict[str, Any]]:
    selected_dates = set(dates)
    selected = [row for row in rows if str(row.get("market_date") or "") in selected_dates]
    selected.sort(key=lambda row: (str(row["as_of_utc"]), str(row["symbol"])))
    keys = [(str(row.get("symbol") or ""), str(row.get("as_of_utc") or "")) for row in selected]
    if not selected or any(not symbol or not as_of for symbol, as_of in keys):
        raise ValueError("sample contains missing symbol or as_of_utc")
    if len(set(keys)) != len(keys):
        raise ValueError("sample contains duplicate point-in-time keys")
    return selected


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--date-count", type=int, default=48)
    parser.add_argument("--minimum-rows-per-date", type=int, default=400)
    args = parser.parse_args()
    rows = read_jsonl(args.base)
    dates = select_dates(rows, args.date_count, args.minimum_rows_per_date)
    selected = select_rows(rows, dates)
    write_jsonl(args.output, selected)
    print(json.dumps({
        "status": "complete", "research_only": True, "execution_enabled": False,
        "date_count": len(dates), "dates": dates, "rows": len(selected),
    }, indent=2))


if __name__ == "__main__":
    main()
