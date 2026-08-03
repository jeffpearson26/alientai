from __future__ import annotations

"""Build point-in-time earnings context for an AI/semiconductor panel."""

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def timestamp(value: Any) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def visible_earnings_features(
    events: Sequence[Mapping[str, Any]],
    as_of_utc: str,
) -> dict[str, Any]:
    cutoff = timestamp(as_of_utc)
    visible = sorted(
        (
            event for event in events
            if event.get("available_at_utc")
            and timestamp(event["available_at_utc"]) <= cutoff
            and event.get("is_training_eligible", True)
        ),
        key=lambda event: timestamp(event["available_at_utc"]),
    )
    if not visible:
        return {
            "narrative_earnings_available": False,
            "narrative_fund_eps_surprise_pct": 0.0,
            "narrative_fund_eps_surprise_pct_missing": True,
            "narrative_fund_days_since_report": 0.0,
            "narrative_fund_days_since_report_missing": True,
            "narrative_fund_eps_beat_streak": 0,
            "narrative_fund_eps_miss_streak": 0,
            "narrative_earnings_visible_count": 0,
            "narrative_earnings_latest_available_at_utc": None,
        }
    latest = visible[-1]
    surprise = number(latest.get("surprise_percentage"))
    beat_streak = miss_streak = 0
    for event in reversed(visible):
        value = number(event.get("surprise_percentage"))
        if value is None:
            break
        if value > 0 and miss_streak == 0:
            beat_streak += 1
        elif value < 0 and beat_streak == 0:
            miss_streak += 1
        else:
            break
    available = timestamp(latest["available_at_utc"])
    return {
        "narrative_earnings_available": True,
        "narrative_fund_eps_surprise_pct": 0.0 if surprise is None else surprise,
        "narrative_fund_eps_surprise_pct_missing": surprise is None,
        "narrative_fund_days_since_report": (cutoff - available).total_seconds() / 86400.0,
        "narrative_fund_days_since_report_missing": False,
        "narrative_fund_eps_beat_streak": beat_streak,
        "narrative_fund_eps_miss_streak": miss_streak,
        "narrative_earnings_visible_count": len(visible),
        "narrative_earnings_latest_available_at_utc": latest["available_at_utc"],
    }


def attach_earnings(
    panel_rows: Iterable[Mapping[str, Any]],
    earnings_rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    events: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for event in earnings_rows:
        symbol = str(event.get("ticker") or "").upper()
        if symbol:
            events[symbol].append(event)
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for source in panel_rows:
        symbol = str(source.get("symbol") or "").upper()
        market_date = str(source.get("market_date") or "")[:10]
        key = (symbol, market_date)
        if not all(key) or key in seen:
            raise ValueError(f"invalid or duplicate panel key: {key}")
        seen.add(key)
        as_of = source.get("as_of_utc")
        if not as_of:
            raise ValueError(f"missing as_of_utc for {symbol}|{market_date}")
        row = dict(source)
        row.update(visible_earnings_features(events.get(symbol, ()), str(as_of)))
        output.append(row)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--earnings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = attach_earnings(read_jsonl(args.panel), read_jsonl(args.earnings))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "rows": len(rows),
        "available_rows": sum(row["narrative_earnings_available"] for row in rows),
        "symbols": len({row["symbol"] for row in rows}),
        "dates": len({row["market_date"] for row in rows}),
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
