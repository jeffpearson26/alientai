"""Prepare unique point-in-time natural-universe news requests for archival."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


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


def normalized_request(row: Dict[str, Any]) -> Dict[str, str]:
    symbol = str(row.get("symbol") or "").strip().upper()
    market_date = str(row.get("market_date") or "").strip()
    as_of_utc = str(row.get("as_of_utc") or "").strip()
    if not symbol or not market_date or not as_of_utc:
        raise ValueError("every source row requires symbol, market_date, and as_of_utc")
    try:
        datetime.fromisoformat(as_of_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid as_of_utc for {symbol} on {market_date}: {as_of_utc}") from exc
    return {
        "symbol": symbol,
        "market_date": market_date,
        "as_of_utc": as_of_utc,
        "study_role": "natural",
    }


def prepare_requests(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, str]]:
    requests: Dict[tuple[str, str], Dict[str, str]] = {}
    for row in rows:
        request = normalized_request(row)
        key = (request["symbol"], request["as_of_utc"])
        if key in requests:
            raise ValueError(f"duplicate point-in-time request: {key[0]}|{key[1]}")
        requests[key] = request
    if not requests:
        raise ValueError("no valid research requests were supplied")
    return sorted(requests.values(), key=lambda item: (item["as_of_utc"], item["symbol"]))


def write_jsonl(path: Path, rows: Iterable[Dict[str, str]]) -> None:
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
    args = parser.parse_args()
    requests = prepare_requests(read_jsonl(args.base))
    write_jsonl(args.output, requests)
    print(json.dumps({"status": "complete", "research_only": True, "requests": len(requests)}, indent=2))


if __name__ == "__main__":
    main()
