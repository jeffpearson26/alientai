"""Attach point-in-time compiled news features to a natural research panel."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
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


def key(row: Dict[str, Any]) -> tuple[str, str]:
    symbol = str(row.get("symbol") or "").strip().upper()
    as_of = str(row.get("as_of_utc") or "").strip()
    if not symbol or not as_of:
        raise ValueError("every panel row requires symbol and as_of_utc")
    return symbol, as_of


def index_news(rows: Iterable[Dict[str, Any]]) -> Dict[tuple[str, str], Dict[str, Any]]:
    indexed: Dict[tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        row_key = key(row)
        if row_key in indexed:
            raise ValueError(f"duplicate news feature key: {row_key[0]}|{row_key[1]}")
        indexed[row_key] = row
    return indexed


def join_panel(base_rows: Iterable[Dict[str, Any]], news_rows: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    news = index_news(news_rows)
    output: list[Dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for base in base_rows:
        row_key = key(base)
        if row_key in seen:
            raise ValueError(f"duplicate base panel key: {row_key[0]}|{row_key[1]}")
        seen.add(row_key)
        feature = news.get(row_key)
        if feature is None:
            output.append({
                **base,
                "news_available": False,
                "news_missing_reason": "archive_response_missing",
                "news_source": "alpha_vantage_news_sentiment_archive",
            })
            continue
        if feature.get("news_available") is not True:
            raise ValueError(f"news row is not available for {row_key[0]}|{row_key[1]}")
        output.append({
            **base,
            **{name: value for name, value in feature.items() if name not in {"symbol", "as_of_utc", "source"}},
            "news_source": feature.get("source"),
        })
    extra = set(news) - seen
    if extra:
        example = sorted(extra)[0]
        raise ValueError(f"news includes key absent from base panel: {example[0]}|{example[1]}")
    return output


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--news", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = join_panel(read_jsonl(args.base), read_jsonl(args.news))
    write_jsonl(args.output, rows)
    print(json.dumps({
        "status": "complete", "research_only": True, "execution_enabled": False,
        "rows": len(rows), "news_available": sum(row.get("news_available") is True for row in rows),
    }, indent=2))


if __name__ == "__main__":
    main()
