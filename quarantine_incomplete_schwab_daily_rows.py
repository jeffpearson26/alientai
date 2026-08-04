from __future__ import annotations

"""Quarantine one explicitly identified incomplete Schwab daily row per symbol."""

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_symbols(paths: list[Path]) -> list[str]:
    return list(
        dict.fromkeys(
            line.split(",", 1)[0].strip().upper()
            for path in paths
            for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    )


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan_quarantine(
    path: Path, stored_date: str
) -> tuple[list[dict[str, str]], dict[str, Any] | None]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    matching = [index for index, row in enumerate(rows) if row.get("date") == stored_date]
    if not matching:
        return rows, None
    if matching != [len(rows) - 1]:
        raise ValueError(f"{path}: target date must occur exactly once as the final row")
    removed = rows[-1]
    return rows[:-1], {
        "path": str(path),
        "sha256_before": file_sha256(path),
        "stored_date": stored_date,
        "row": removed,
        "fields": fields,
    }


def write_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, action="append", required=True)
    parser.add_argument("--stored-date", required=True)
    parser.add_argument("--quarantine-output", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    plans = []
    for symbol in read_symbols(args.symbols_file):
        path = args.daily_dir / f"{symbol.replace('/', '-').replace('.', '-')}_schwab_1d_max.csv"
        if not path.exists():
            continue
        remaining, record = plan_quarantine(path, args.stored_date)
        if record:
            plans.append((path, remaining, record))
    report = {
        "status": "complete",
        "research_only": True,
        "stored_date": args.stored_date,
        "rows_found": len(plans),
        "applied": args.apply,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "records": [record for _, _, record in plans],
    }
    if args.apply and plans:
        args.quarantine_output.parent.mkdir(parents=True, exist_ok=True)
        args.quarantine_output.write_text(
            "\n".join(json.dumps(record, sort_keys=True) for _, _, record in plans)
            + "\n",
            encoding="utf-8",
        )
        for path, remaining, record in plans:
            write_rows(path, list(record["fields"]), remaining)
    print(json.dumps({key: report[key] for key in report if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
