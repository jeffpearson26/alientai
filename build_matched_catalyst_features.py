from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def key(row: Mapping[str, Any], *, news: bool = False) -> tuple[str, str]:
    date = str(row.get("as_of_utc") or "")[:10] if news else str(row.get("market_date") or "")
    return str(row.get("symbol") or "").upper(), date


def unique_rows(rows: Iterable[Mapping[str, Any]], *, news: bool = False) -> dict[tuple[str, str], Mapping[str, Any]]:
    output = {}
    for row in rows:
        item_key = key(row, news=news)
        if item_key in output:
            raise ValueError(f"duplicate catalyst feature key: {item_key[0]}|{item_key[1]}")
        output[item_key] = row
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--news", type=Path, required=True)
    parser.add_argument("--options", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    news = unique_rows(read_jsonl(args.news), news=True)
    options = unique_rows(read_jsonl(args.options))
    rows, missing = [], 0
    for base in read_jsonl(args.base):
        item_key = key(base)
        news_row, option_row = news.get(item_key), options.get(item_key)
        if news_row is None or option_row is None:
            missing += 1
            continue
        merged = dict(base)
        merged.update({name: value for name, value in news_row.items() if name not in {"symbol", "as_of_utc"}})
        merged.update({name: value for name, value in option_row.items() if name not in {"symbol", "market_date"}})
        rows.append(merged)
    if missing:
        raise ValueError(f"missing catalyst features for {missing} base rows")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({"status": "complete", "rows": len(rows), "missing": missing, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
