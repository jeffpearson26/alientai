"""Create an explicit research-only JSONL slice for a documented symbol basket."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


def load_symbols(path: Path) -> set[str]:
    symbols = {
        line.strip().upper() for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if not symbols:
        raise ValueError("symbols file is empty")
    return symbols


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"expected object at {path}:{line_number}")
            yield row


def slice_rows(rows: Iterable[dict[str, Any]], symbols: set[str]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            raise ValueError("source row is missing symbol")
        if symbol in symbols:
            output.append(row)
    if not output:
        raise ValueError("no source rows match the requested universe")
    return output


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--symbols", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = slice_rows(read_jsonl(args.input), load_symbols(args.symbols))
    write_jsonl(args.output, rows)
    print(json.dumps({"status": "complete", "research_only": True, "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
