from __future__ import annotations

"""Extend archived option features with one prior-session call-history snapshot."""

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from alientai_v2.research.unusual_call_activity import unusual_call_features


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def target_features(
    historical: Sequence[dict[str, Any]],
    current: Sequence[dict[str, Any]],
    target_date: str,
) -> list[dict[str, Any]]:
    symbols = {str(row.get("symbol") or "").upper() for row in current}
    if not symbols or len(current) != len(symbols):
        raise ValueError("current option rows require one unique row per symbol")
    rows = [
        row for row in historical
        if str(row.get("symbol") or "").upper() in symbols
        and str(row.get("market_date") or "") < target_date
    ] + [
        row for row in current if str(row.get("market_date") or "") == target_date
    ]
    features = unusual_call_features(rows)
    result = [row for row in features if row["market_date"] == target_date]
    if {row["symbol"] for row in result} != symbols:
        raise ValueError("failed to produce exact target call features")
    return sorted(result, key=lambda row: row["symbol"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--target-date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = target_features(
        read_jsonl(args.historical), read_jsonl(args.current), args.target_date
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({
        "status": "complete",
        "target_date": args.target_date,
        "rows": len(rows),
        "unusual": sum(bool(row["call_volume_unusual"]) for row in rows),
        "minimum_history": min(row["call_activity_history_count"] for row in rows),
    }, indent=2))


if __name__ == "__main__":
    main()
