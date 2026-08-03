from __future__ import annotations

"""Append exact Alpha Vantage outcomes for frozen narrative observations."""

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping


COST_PCT = 0.25


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_daily(path: Path) -> list[tuple[str, float, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    series = payload.get("Time Series (Daily)") or {}
    return sorted(
        (day, float(values["1. open"]), float(values["4. close"]))
        for day, values in series.items()
    )


def build_outcomes(
    observations: Iterable[Mapping[str, Any]],
    daily_by_symbol: Mapping[str, tuple[list[tuple[str, float, float]], str]],
    as_of_market_date: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    as_of = date.fromisoformat(as_of_market_date)
    complete, pending = [], []
    for source in observations:
        row = dict(source)
        symbol = str(row.get("symbol") or "").upper()
        decision = str(row.get("market_date") or "")[:10]
        model_id = str(row.get("model_id") or "")
        horizon = int(row.get("target_horizon_sessions") or 0)
        if not symbol or not decision or not model_id or horizon <= 0:
            raise ValueError("journal observation lacks frozen outcome identity")
        if symbol not in daily_by_symbol:
            raise ValueError(f"missing daily source for {symbol}")
        daily, source_hash = daily_by_symbol[symbol]
        positions = {item[0]: index for index, item in enumerate(daily)}
        decision_index = positions.get(decision)
        identity = {
            "model_id": model_id,
            "model_sha256": row.get("model_sha256"),
            "symbol": symbol,
            "decision_market_date": decision,
            "target_horizon_sessions": horizon,
        }
        if decision_index is None:
            pending.append({**identity, "status": "pending_decision_candle"})
            continue
        entry_index = decision_index + 1
        exit_index = decision_index + horizon
        if exit_index >= len(daily) or entry_index >= len(daily):
            pending.append({**identity, "status": "pending_candle_coverage"})
            continue
        entry_date, entry_open, _ = daily[entry_index]
        exit_date, _, exit_close = daily[exit_index]
        if date.fromisoformat(exit_date) > as_of:
            pending.append({
                **identity,
                "entry_market_date": entry_date,
                "expected_exit_market_date": exit_date,
                "status": "pending_horizon",
            })
            continue
        net = (exit_close / entry_open - 1.0) * 100.0 - COST_PCT
        complete.append({
            **identity,
            "entry_market_date": entry_date,
            "entry_open": entry_open,
            "exit_market_date": exit_date,
            "exit_close": exit_close,
            "net_return_pct": net,
            "round_trip_cost_pct": COST_PCT,
            "source": "Alpha Vantage TIME_SERIES_DAILY",
            "source_file_sha256": source_hash,
            "status": "complete",
            "research_only": True,
            "execution_decision": "AVOID",
        })
    return complete, pending


def append_unique(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    existing = {
        (row["model_id"], row["symbol"], row["decision_market_date"])
        for row in read_jsonl(path)
    }
    additions = []
    for source in rows:
        row = dict(source)
        key = (row["model_id"], row["symbol"], row["decision_market_date"])
        if key not in existing:
            additions.append(row)
            existing.add(key)
    if additions:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            for row in additions:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    return len(additions)


def summarize(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[float]] = defaultdict(list)
    dates: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row.get("status") == "complete":
            grouped[row["model_id"]].append(float(row["net_return_pct"]))
            dates[row["model_id"]].add(row["decision_market_date"])
    return {
        "research_only": True,
        "execution_enabled": False,
        "records": [{
            "model_id": model,
            "signals": len(values),
            "decision_dates": len(dates[model]),
            "mean_net_return_pct": sum(values) / len(values),
            "median_net_return_pct": median(values),
            "win_rate_after_cost": sum(value > 0 for value in values) / len(values),
            "worst_net_return_pct": min(values),
            "best_net_return_pct": max(values),
        } for model, values in sorted(grouped.items())],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--daily-root", type=Path, required=True)
    parser.add_argument("--as-of-market-date", required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    observations = read_jsonl(args.journal)
    symbols = sorted({str(row["symbol"]).upper() for row in observations})
    daily = {}
    for symbol in symbols:
        path = args.daily_root / f"{symbol}_daily.json"
        if not path.exists():
            raise ValueError(f"missing daily source for {symbol}")
        daily[symbol] = (load_daily(path), hashlib.sha256(path.read_bytes()).hexdigest())
    complete, pending = build_outcomes(observations, daily, args.as_of_market_date)
    appended = append_unique(args.outcomes, complete)
    payload = summarize(read_jsonl(args.outcomes))
    payload["pending"] = pending
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "complete", "mature": len(complete), "pending": len(pending),
        "appended": appended, "research_only": True, "execution_enabled": False,
    }, indent=2))


if __name__ == "__main__":
    main()
