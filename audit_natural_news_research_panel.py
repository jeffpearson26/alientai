"""Fail-closed timing and coverage audit for a natural point-in-time news panel."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
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


def parse_utc(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("timestamp is required")
    try:
        result = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {text}") from exc
    if result.tzinfo is None:
        raise ValueError(f"timestamp must include timezone: {text}")
    return result.astimezone(timezone.utc)


def audit_rows(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    seen: set[tuple[str, str]] = set()
    total = available = missing = future_visible = malformed_missing = 0
    first = last = None
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        as_of = parse_utc(row.get("as_of_utc"))
        if not symbol:
            raise ValueError("symbol is required")
        row_key = (symbol, as_of.isoformat())
        if row_key in seen:
            raise ValueError(f"duplicate panel key: {symbol}|{as_of.isoformat()}")
        seen.add(row_key)
        total += 1
        first = as_of if first is None or as_of < first else first
        last = as_of if last is None or as_of > last else last
        if row.get("news_available") is True:
            available += 1
            latest = row.get("news_latest_published_utc")
            if latest:
                if parse_utc(latest) > as_of:
                    future_visible += 1
        else:
            missing += 1
            if not str(row.get("news_missing_reason") or "").strip():
                malformed_missing += 1
    if not total:
        raise ValueError("panel is empty")
    if future_visible or malformed_missing:
        raise ValueError(
            f"panel timing/coverage audit failed: future_visible={future_visible}, malformed_missing={malformed_missing}"
        )
    return {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "rows": total,
        "unique_keys": len(seen),
        "news_available_rows": available,
        "news_missing_rows": missing,
        "coverage_pct": round(100.0 * available / total, 6),
        "future_visible_news_rows": future_visible,
        "malformed_missing_rows": malformed_missing,
        "first_as_of_utc": first.isoformat(),
        "last_as_of_utc": last.isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_rows(read_jsonl(args.panel))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
