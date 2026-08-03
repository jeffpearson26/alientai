from __future__ import annotations

"""Derive an exact Alpha Vantage outcome request from frozen competition picks."""

import argparse
import json
from pathlib import Path
from typing import Any

from build_prospective_event_requests import build_requests


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def frozen_symbols(
    submissions: list[dict[str, Any]],
    decision_date: str,
) -> list[str]:
    selected = [
        row
        for row in submissions
        if str(row.get("decision_date") or "") == decision_date
    ]
    if not selected:
        raise ValueError("no competition submissions exist for decision date")
    identities: set[tuple[str, str, str]] = set()
    values: set[str] = set()
    for row in selected:
        if row.get("research_only") is not True:
            raise ValueError("competition submission is not research-only")
        if str(row.get("execution_decision") or "") != "AVOID":
            raise ValueError("competition submission does not fail closed")
        if str(row.get("status") or "") != "frozen_pending":
            raise ValueError("competition submission is not frozen pending")
        identity = (
            str(row.get("round_id") or ""),
            str(row.get("participant") or "").casefold(),
            decision_date,
        )
        if not identity[0] or not identity[1] or identity in identities:
            raise ValueError("competition submission identity is invalid or duplicate")
        identities.add(identity)
        declared_count = int(row.get("pick_count") or 0)
        picks = [
            str(symbol).strip().upper()
            for symbol in row.get("picks") or []
        ]
        if declared_count != len(picks) or len(picks) != len(set(picks)):
            raise ValueError("competition submission pick count is inconsistent")
        values.update(symbol for symbol in picks if symbol)
    if not values:
        raise ValueError("all competition submissions abstained")
    return sorted(values)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--as-of-utc", required=True)
    parser.add_argument("--symbols-output", type=Path, required=True)
    parser.add_argument("--events-output", type=Path, required=True)
    args = parser.parse_args()
    values = frozen_symbols(read_jsonl(args.journal), args.decision_date)
    events = build_requests(values, args.decision_date, args.as_of_utc)
    args.symbols_output.parent.mkdir(parents=True, exist_ok=True)
    args.symbols_output.write_text(
        "".join(symbol + "\n" for symbol in values),
        encoding="utf-8",
    )
    args.events_output.parent.mkdir(parents=True, exist_ok=True)
    args.events_output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in events),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "decision_date": args.decision_date,
                "symbols": len(values),
                "research_only": True,
                "execution_enabled": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
