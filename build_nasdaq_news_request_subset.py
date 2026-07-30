from __future__ import annotations

"""Create a deterministic Nasdaq-only subset of point-in-time news requests.

The source events are already price/option-labelled research rows.  This tool
only selects request identities; it neither downloads anything nor changes any
execution setting.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_symbols(path: Path) -> set[str]:
    return {
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def select_requests(rows: Iterable[dict[str, Any]], symbols: set[str]) -> list[dict[str, Any]]:
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        as_of = str(row.get("as_of_utc") or "").strip()
        if symbol not in symbols or not as_of:
            continue
        key = (symbol, as_of)
        prior = selected.get(key)
        if prior is not None and prior != row:
            raise ValueError(f"conflicting duplicate request: {symbol}|{as_of}")
        selected[key] = row
    if not selected:
        raise ValueError("no Nasdaq request rows selected")
    return [selected[key] for key in sorted(selected, key=lambda value: (value[1], value[0]))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = select_requests(read_jsonl(args.events), read_symbols(args.symbols_file))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    dates = sorted({str(row["as_of_utc"])[:10] for row in rows})
    print(json.dumps({"status": "complete", "research_only": True, "rows": len(rows), "dates": len(dates), "first_date": dates[0], "last_date": dates[-1]}, indent=2))


if __name__ == "__main__":
    main()
