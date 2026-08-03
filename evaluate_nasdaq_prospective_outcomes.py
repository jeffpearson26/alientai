from __future__ import annotations

"""Append mature five-session outcomes for frozen Schwab Nasdaq journals."""

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping


ROUND_TRIP_COST_PCT = 0.25


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_candles(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return sorted(csv.DictReader(handle), key=lambda row: row["date"])


def schwab_session_date(stored_date: str) -> str:
    return (date.fromisoformat(stored_date) + timedelta(days=1)).isoformat()


def build_outcomes(
    *,
    observations: Iterable[Mapping[str, Any]],
    daily_dir: Path,
    as_of_session_date: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    as_of = date.fromisoformat(as_of_session_date)
    complete: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    cache: dict[str, tuple[list[dict[str, str]], str]] = {}
    for item in observations:
        row = dict(item)
        symbol = str(row.get("symbol") or "").strip().upper()
        model_id = str(row.get("model_id") or "").strip()
        stored_entry_date = str(row.get("market_date") or "")
        session_entry_date = str(row.get("market_session_date") or "")
        horizon = int(row.get("target_horizon_sessions") or 0)
        if not symbol or not model_id or horizon <= 0:
            raise ValueError("journal observation lacks frozen outcome identity")
        if schwab_session_date(stored_entry_date) != session_entry_date:
            raise ValueError(f"legacy Schwab date mapping mismatch for {symbol}")
        if symbol not in cache:
            path = daily_dir / f"{symbol}_schwab_1d_max.csv"
            if not path.exists():
                raise ValueError(f"missing frozen Schwab history for {symbol}")
            cache[symbol] = (load_candles(path), sha256(path))
        candles, source_hash = cache[symbol]
        positions = {
            str(candle["date"]): index
            for index, candle in enumerate(candles)
        }
        entry_index = positions.get(stored_entry_date)
        if entry_index is None:
            raise ValueError(f"entry candle missing for {symbol}")
        entry_close = float(candles[entry_index]["close"])
        recorded_entry = float(row.get("entry_close") or 0.0)
        if abs(entry_close - recorded_entry) > 1e-8:
            raise ValueError(f"frozen entry close changed for {symbol}")
        exit_index = entry_index + horizon
        identity = {
            "model_id": model_id,
            "model_sha256": row.get("model_sha256"),
            "symbol": symbol,
            "entry_market_date": stored_entry_date,
            "entry_session_date": session_entry_date,
            "target_horizon_sessions": horizon,
        }
        if exit_index >= len(candles):
            pending.append({**identity, "status": "pending_candle_coverage"})
            continue
        exit_candle = candles[exit_index]
        exit_session = schwab_session_date(str(exit_candle["date"]))
        if date.fromisoformat(exit_session) > as_of:
            pending.append(
                {
                    **identity,
                    "expected_exit_session_date": exit_session,
                    "status": "pending_horizon",
                }
            )
            continue
        exit_close = float(exit_candle["close"])
        net_return = (exit_close / entry_close - 1.0) * 100.0
        net_return -= ROUND_TRIP_COST_PCT
        complete.append(
            {
                **identity,
                "entry_close": entry_close,
                "exit_stored_market_date": exit_candle["date"],
                "exit_session_date": exit_session,
                "exit_close": exit_close,
                "net_return_pct": net_return,
                "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
                "source": "Schwab local daily max-history archive",
                "source_file_sha256": source_hash,
                "status": "complete",
                "research_only": True,
                "execution_decision": "AVOID",
            }
        )
    return complete, pending


def append_unique(path: Path, outcomes: Iterable[Mapping[str, Any]]) -> int:
    existing = {
        (
            str(row.get("model_id")),
            str(row.get("symbol")),
            str(row.get("entry_market_date")),
            int(row.get("target_horizon_sessions") or 0),
        )
        for row in read_jsonl(path)
    }
    additions = []
    for item in outcomes:
        row = dict(item)
        key = (
            str(row.get("model_id")),
            str(row.get("symbol")),
            str(row.get("entry_market_date")),
            int(row.get("target_horizon_sessions") or 0),
        )
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
        if str(row.get("status")) != "complete":
            continue
        model = str(row["model_id"])
        grouped[model].append(float(row["net_return_pct"]))
        dates[model].add(str(row["entry_session_date"]))
    records = []
    for model, values in sorted(grouped.items()):
        records.append(
            {
                "model_id": model,
                "signals": len(values),
                "decision_dates": len(dates[model]),
                "mean_net_return_pct": sum(values) / len(values),
                "median_net_return_pct": median(values),
                "win_rate_after_cost": (
                    sum(value > 0 for value in values) / len(values)
                ),
                "worst_net_return_pct": min(values),
                "best_net_return_pct": max(values),
            }
        )
    return {
        "research_only": True,
        "execution_enabled": False,
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--as-of-session-date", required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    complete, pending = build_outcomes(
        observations=read_jsonl(args.journal),
        daily_dir=args.daily_dir,
        as_of_session_date=args.as_of_session_date,
    )
    appended = append_unique(args.outcomes, complete)
    payload = summarize(read_jsonl(args.outcomes))
    payload["pending"] = pending
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "mature": len(complete),
                "pending": len(pending),
                "appended": appended,
                "research_only": True,
                "execution_enabled": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
