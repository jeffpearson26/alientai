from __future__ import annotations

import argparse
import csv
import gzip
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from alientai_v2.features.premarket_features import build_premarket_features
from download_alpha_vantage_matched_premarket import archive_path, read_jsonl


# A natural-universe build touches roughly 3,400 symbol-month files.  Keeping
# those parsed months avoids repeatedly decompressing the same file when rows
# are ordered by market date rather than by symbol.
@lru_cache(maxsize=4096)
def read_month(path_text: str) -> List[Dict[str, str]]:
    path = Path(path_text)
    if not path.exists():
        return []
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


@lru_cache(maxsize=4096)
def index_month(path_text: str) -> Dict[str, List[Dict[str, str]]]:
    by_date: Dict[str, List[Dict[str, str]]] = {}
    for row in read_month(path_text):
        timestamp = str(row.get("timestamp") or "")
        if len(timestamp) >= 10:
            by_date.setdefault(timestamp[:10], []).append(row)
    for rows in by_date.values():
        rows.sort(key=lambda row: str(row.get("timestamp") or ""))
    return by_date


def event_context(path_text: str, market_date: str) -> List[Dict[str, str]]:
    """Return only rows needed to calculate one day's premarket features."""
    by_date = index_month(path_text)
    dates = sorted(day for day in by_date if day < market_date)[-10:]
    context: List[Dict[str, str]] = []
    for day in dates:
        rows = by_date[day]
        premarket = [
            row for row in rows
            if " 04:00" <= str(row.get("timestamp") or "")[10:16] <= " 09:25"
        ]
        regular = [
            row for row in rows
            if " 09:30" <= str(row.get("timestamp") or "")[10:16] <= " 16:00"
        ]
        context.extend(premarket)
        if regular:
            context.append(regular[-1])
    context.extend(by_date.get(market_date, []))
    return context


def build_rows(events: List[Dict[str, Any]], archive: Path) -> List[Dict[str, Any]]:
    output = []
    for event in events:
        symbol = str(event.get("symbol") or "").strip().upper()
        market_date = str(event.get("market_date") or "").strip()
        row = {"symbol": symbol, "market_date": market_date}
        # Preserve matched-study identity only for actual matched-study input.
        # Natural-universe output must not acquire empty study fields because
        # downstream leakage guards intentionally reject that schema.
        for field in ("study_event_id", "study_role", "study_label"):
            if field in event and event.get(field) is not None:
                row[field] = event[field]
        if symbol and len(market_date) == 10:
            month = market_date[:7]
            candles = event_context(str(archive_path(archive, symbol, month)), market_date)
            row.update(build_premarket_features(candles, market_date))
        else:
            row["premarket_available"] = False
        output.append(row)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = build_rows(read_jsonl(args.events), args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({
        "status": "complete", "rows": len(rows),
        "available": sum(bool(row.get("premarket_available")) for row in rows),
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
