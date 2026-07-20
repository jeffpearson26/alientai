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


@lru_cache(maxsize=256)
def read_month(path_text: str) -> List[Dict[str, str]]:
    path = Path(path_text)
    if not path.exists():
        return []
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_rows(events: List[Dict[str, Any]], archive: Path) -> List[Dict[str, Any]]:
    output = []
    for event in events:
        symbol = str(event.get("symbol") or "").strip().upper()
        market_date = str(event.get("market_date") or "").strip()
        row = {
            "study_event_id": event.get("study_event_id"), "study_role": event.get("study_role"),
            "study_label": event.get("study_label"), "symbol": symbol, "market_date": market_date,
        }
        if symbol and len(market_date) == 10:
            month = market_date[:7]
            candles = read_month(str(archive_path(archive, symbol, month)))
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
