"""Stream a large JSONL research table into an explicit symbol universe."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_symbols(path: Path) -> set[str]:
    return {
        line.strip().upper()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def filter_rows(source: Path, destination: Path, allowed: set[str]) -> dict:
    rows = 0
    found: set[str] = set()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open(encoding="utf-8") as input_handle, destination.open(
        "w", encoding="utf-8", newline="\n"
    ) as output_handle:
        for line in input_handle:
            if not line.strip():
                continue
            row = json.loads(line)
            symbol = str(row.get("symbol") or "").upper()
            if symbol not in allowed:
                continue
            output_handle.write(json.dumps(row, sort_keys=True) + "\n")
            found.add(symbol)
            rows += 1
    return {
        "status": "complete",
        "rows": rows,
        "requested_symbols": len(allowed),
        "found_symbols": sorted(found),
        "missing_symbols": sorted(allowed - found),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter a JSONL table to an explicit symbol universe.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()
    result = filter_rows(args.input, args.output, read_symbols(args.symbols_file))
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
