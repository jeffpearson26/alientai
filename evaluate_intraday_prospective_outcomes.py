from __future__ import annotations

"""Append completed 20/60-minute outcomes for frozen prospective observations."""

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from build_ai_semiconductor_20min_panel import intraday_label
from build_matched_premarket_features import index_month
from download_alpha_vantage_matched_premarket import archive_path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def completed_outcomes(
    observations: Sequence[Mapping[str, Any]], archive: Path
) -> list[dict[str, Any]]:
    output = []
    for row in observations:
        symbol, market_date = str(row["symbol"]), str(row["market_date"])
        horizon = int(row["horizon_minutes"])
        candles = index_month(str(archive_path(archive, symbol, market_date[:7]))).get(market_date, [])
        label = intraday_label(candles, market_date, horizon)
        if label is None:
            continue
        output.append({
            "model_id": row["model_id"],
            "model_sha256": row["model_sha256"],
            "market_date": market_date,
            "symbol": symbol,
            "rank": row["rank"],
            "model_score": row["model_score"],
            "horizon_minutes": horizon,
            **label,
            "status": "complete",
            "research_only": True,
            "execution_decision": "AVOID",
        })
    return output


def append_unique(path: Path, rows: Sequence[Mapping[str, Any]]) -> int:
    existing = {
        (row["model_id"], row["market_date"], row["symbol"])
        for row in read_jsonl(path)
    } if path.exists() else set()
    additions = [
        row for row in rows
        if (row["model_id"], row["market_date"], row["symbol"]) not in existing
    ]
    if additions:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            for row in additions:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    return len(additions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    args = parser.parse_args()
    rows = completed_outcomes(read_jsonl(args.journal), args.archive)
    additions = append_unique(args.outcomes, rows)
    print(json.dumps({
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "available_outcomes": len(rows),
        "appended": additions,
        "outcomes": str(args.outcomes),
    }, indent=2))


if __name__ == "__main__":
    main()
