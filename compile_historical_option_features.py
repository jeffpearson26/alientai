from __future__ import annotations

"""Compile one point-in-time option feature row per historical symbol/date."""

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from alientai_v2.features.option_chain_features import option_chain_features
from alientai_v2.research.historical_call_evaluator import chain_path, load_chain


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def unique_event_closes(rows: Iterable[Mapping[str, Any]]) -> dict[tuple[str, str], float]:
    """Return the unique (symbol, event-date) close, rejecting inconsistent duplicates."""
    output: dict[tuple[str, str], float] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        day = str(row.get("market_date") or "").strip()
        try:
            close = float(row.get("close"))
        except (TypeError, ValueError):
            continue
        if not symbol or len(day) != 10 or close <= 0:
            continue
        key = (symbol, day)
        previous = output.get(key)
        if previous is not None and abs(previous - close) > 1e-6:
            raise ValueError(f"inconsistent close for duplicate event key {symbol}|{day}")
        output[key] = close
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--chains", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    event_closes = unique_event_closes(read_jsonl(args.events))
    rows, missing = [], 0
    for (symbol, day), close in sorted(event_closes.items(), key=lambda item: (item[0][1], item[0][0])):
        path = chain_path(args.chains, symbol, day)
        if not path.exists():
            missing += 1
            continue
        rows.append({
            "symbol": symbol, "market_date": day, "option_available": True,
            **option_chain_features(load_chain(path), close),
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({"status": "complete", "unique_event_keys": len(event_closes), "rows": len(rows), "missing": missing, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
