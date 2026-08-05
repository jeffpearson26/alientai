from __future__ import annotations

"""Append mature outcomes for the frozen autonomous 20-session journal."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping

from build_nasdaq_qqq_spy_60session_panel import load_adjusted_daily


HORIZON_SESSIONS = 20
ROUND_TRIP_COST_PCT = 0.25
MODEL_FAMILY = (
    "transparent cross-sectional 126/60-session momentum "
    "plus inverse 60-session volatility"
)


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


def build_outcomes(
    *,
    journal_rows: Iterable[Mapping[str, Any]],
    daily_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    complete: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    cache: dict[str, tuple[list[dict[str, Any]], str]] = {}
    for observation in journal_rows:
        if observation.get("model_family") != MODEL_FAMILY:
            raise ValueError("journal model family does not match frozen model")
        if float(observation.get("round_trip_cost_pct") or 0.0) != (
            ROUND_TRIP_COST_PCT
        ):
            raise ValueError("journal cost does not match frozen model")
        decision_date = str(observation.get("decision_date") or "")
        report_hash = str(observation.get("frozen_report_sha256") or "")
        if not decision_date or not report_hash:
            raise ValueError("journal observation lacks frozen identity")
        for selection in observation.get("selections") or []:
            symbol = str(selection.get("symbol") or "").strip().upper()
            if not symbol:
                raise ValueError("journal selection lacks symbol")
            if symbol not in cache:
                source_path = daily_root / f"{symbol}_daily.json"
                if not source_path.exists():
                    raise ValueError(f"missing adjusted daily source for {symbol}")
                cache[symbol] = (
                    load_adjusted_daily(source_path),
                    sha256(source_path),
                )
            candles, source_hash = cache[symbol]
            positions = {
                str(candle["market_date"]): index
                for index, candle in enumerate(candles)
            }
            decision_index = positions.get(decision_date)
            identity = {
                "model_family": MODEL_FAMILY,
                "frozen_report_sha256": report_hash,
                "decision_date": decision_date,
                "symbol": symbol,
                "rank": int(selection.get("rank") or 0),
                "horizon_sessions": HORIZON_SESSIONS,
            }
            if decision_index is None:
                raise ValueError(
                    f"decision candle {decision_date} missing for {symbol}"
                )
            entry_index = decision_index + 1
            exit_index = decision_index + HORIZON_SESSIONS
            if exit_index >= len(candles):
                pending.append(
                    {
                        **identity,
                        "status": "PENDING_HORIZON",
                        "available_future_sessions": max(
                            0, len(candles) - decision_index - 1
                        ),
                        "required_future_sessions": HORIZON_SESSIONS,
                    }
                )
                continue
            entry = candles[entry_index]
            exit_row = candles[exit_index]
            entry_open = float(entry["open"])
            exit_close = float(exit_row["close"])
            gross_return = (exit_close / entry_open - 1.0) * 100.0
            complete.append(
                {
                    **identity,
                    "status": "COMPLETE",
                    "research_only": True,
                    "execution_enabled": False,
                    "entry_market_date": entry["market_date"],
                    "entry_adjusted_open": entry_open,
                    "exit_market_date": exit_row["market_date"],
                    "exit_adjusted_close": exit_close,
                    "gross_return_pct": gross_return,
                    "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
                    "net_return_pct": (
                        gross_return - ROUND_TRIP_COST_PCT
                    ),
                    "source": "Alpha Vantage full adjusted daily archive",
                    "source_file_sha256": source_hash,
                }
            )
    return complete, pending


def append_unique(
    path: Path, rows: Iterable[Mapping[str, Any]]
) -> int:
    existing = {
        (
            str(row.get("frozen_report_sha256")),
            str(row.get("decision_date")),
            str(row.get("symbol")),
        )
        for row in read_jsonl(path)
    }
    additions: list[dict[str, Any]] = []
    for item in rows:
        row = dict(item)
        key = (
            str(row.get("frozen_report_sha256")),
            str(row.get("decision_date")),
            str(row.get("symbol")),
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
    complete = [
        dict(row) for row in rows if row.get("status") == "COMPLETE"
    ]
    values = [float(row["net_return_pct"]) for row in complete]
    dates = {str(row["decision_date"]) for row in complete}
    symbols: dict[str, int] = defaultdict(int)
    for row in complete:
        symbols[str(row["symbol"])] += 1
    return {
        "research_only": True,
        "execution_enabled": False,
        "model_family": MODEL_FAMILY,
        "horizon_sessions": HORIZON_SESSIONS,
        "signals": len(values),
        "decision_dates": len(dates),
        "symbols": len(symbols),
        "mean_net_return_pct": (
            sum(values) / len(values) if values else None
        ),
        "median_net_return_pct": median(values) if values else None,
        "win_rate_after_cost_pct": (
            100.0 * sum(value > 0 for value in values) / len(values)
            if values
            else None
        ),
        "worst_net_return_pct": min(values) if values else None,
        "best_net_return_pct": max(values) if values else None,
        "largest_symbol_share_pct": (
            100.0 * max(symbols.values()) / len(values)
            if values
            else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--daily-root", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    complete, pending = build_outcomes(
        journal_rows=read_jsonl(args.journal),
        daily_root=args.daily_root,
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
