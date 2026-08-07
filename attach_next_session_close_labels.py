from __future__ import annotations

"""Attach source-consistent next-session-close labels to a research panel."""

import argparse
import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_daily(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return sorted(csv.DictReader(handle), key=lambda row: row["date"])


def schwab_regular_session_date(candle: Mapping[str, Any]) -> date:
    """Return the U.S. session date encoded by a Schwab daily candle.

    Schwab's daily archive timestamps are stored at 21:00/22:00 UTC on the
    preceding Pacific calendar date.  The represented U.S. regular session is
    therefore the following calendar date.  Requiring the timestamp avoids a
    silent one-session label shift.
    """
    raw = str(candle.get("datetime") or "").strip()
    if not raw:
        raise ValueError("Schwab daily candle is missing datetime")
    try:
        timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid Schwab daily datetime") from exc
    return timestamp.date() + timedelta(days=1)


def index_schwab_daily(
    candles: Iterable[Mapping[str, Any]],
) -> dict[date, tuple[Mapping[str, Any], Mapping[str, Any] | None]]:
    """Index each source date and its immediately following stored candle."""
    ordered: list[tuple[date, Mapping[str, Any]]] = []
    seen: set[date] = set()
    for candle in candles:
        try:
            source_day = date.fromisoformat(str(candle.get("date") or ""))
            # Require the timestamp even though price anchoring, not a fixed
            # offset, identifies the source candle.
            schwab_regular_session_date(candle)
        except ValueError as exc:
            raise ValueError("invalid Schwab daily candle identity") from exc
        if source_day in seen:
            raise ValueError(f"duplicate Schwab source date: {source_day}")
        seen.add(source_day)
        ordered.append((source_day, candle))
    ordered.sort(key=lambda item: item[0])
    return {
        source_day: (
            candle,
            ordered[index + 1][1] if index + 1 < len(ordered) else None,
        )
        for index, (source_day, candle) in enumerate(ordered)
    }


def price_anchored_next_session_label_from_index(
    row: Mapping[str, Any],
    daily_index: Mapping[
        date, tuple[Mapping[str, Any], Mapping[str, Any] | None]
    ],
    *,
    round_trip_cost_pct: float,
    close_tolerance_fraction: float = 0.00001,
    maximum_next_session_gap_days: int = 5,
) -> dict[str, Any] | None:
    """Fast indexed implementation of :func:`price_anchored_next_session_label`."""
    symbol = str(row.get("symbol") or "").upper().strip()
    market_date = str(row.get("market_date") or "")
    if not symbol or not market_date or row.get("close") is None:
        raise ValueError("panel row requires symbol, market_date, and close")
    if round_trip_cost_pct < 0.0:
        raise ValueError("round-trip cost cannot be negative")
    decision_day = date.fromisoformat(market_date)
    decision_close = float(row["close"])
    if decision_close <= 0.0:
        raise ValueError("decision close must be positive")
    candidates = []
    for offset in range(-3, 4):
        source_day = decision_day + timedelta(days=offset)
        pair = daily_index.get(source_day)
        if pair is None:
            continue
        current = pair[0]
        try:
            current_close = float(current["close"])
        except (KeyError, TypeError, ValueError):
            continue
        if (
            current_close > 0.0
            and abs(current_close / decision_close - 1.0)
            <= close_tolerance_fraction
        ):
            candidates.append((source_day, pair))
    if not candidates:
        return None
    source_day, (current, future) = min(
        candidates,
        key=lambda item: (
            abs((item[0] - decision_day).days),
            item[0],
        ),
    )
    if future is None:
        return None
    try:
        current_close = float(current["close"])
        future_day = schwab_regular_session_date(future)
        entry_price = float(future["open"])
        exit_price = float(future["close"])
    except (KeyError, TypeError, ValueError):
        return None
    if (
        current_close <= 0.0
        or abs(current_close / decision_close - 1.0)
        > close_tolerance_fraction
        or future_day <= schwab_regular_session_date(current)
        or (
            date.fromisoformat(str(future.get("date") or "")) - source_day
        ).days
        > maximum_next_session_gap_days
        or entry_price <= 0.0
        or exit_price <= 0.0
    ):
        return None
    gross = (exit_price / entry_price - 1.0) * 100.0
    return {
        **dict(row),
        "entry_assumption": "next_regular_session_open",
        "label_entry_market_date": future_day.isoformat(),
        "label_entry_price": entry_price,
        "future_market_date": future_day.isoformat(),
        "label_exit_price": exit_price,
        "label_forward_return_1d_gross_pct": gross,
        "label_forward_return_1d_pct": gross - round_trip_cost_pct,
        "round_trip_cost_pct": round_trip_cost_pct,
        "target_horizon_sessions": 1,
        "label_contract": (
            "decision after completed regular-session close; enter next "
            "regular-session open; exit that session's official close"
        ),
        "daily_source_date": str(future.get("date") or ""),
        "daily_source_datetime": str(future.get("datetime") or ""),
        "decision_daily_source_date": str(current.get("date") or ""),
        "decision_daily_source_datetime": str(
            current.get("datetime") or ""
        ),
        "research_only": True,
        "execution_enabled": False,
    }


def price_anchored_next_session_label(
    row: Mapping[str, Any],
    candles: Iterable[Mapping[str, Any]],
    *,
    round_trip_cost_pct: float,
    close_tolerance_fraction: float = 0.00001,
    maximum_next_session_gap_days: int = 5,
) -> dict[str, Any] | None:
    """Label the next session open-to-close after an exact decision close.

    The source panel's ``market_date`` is the true U.S. session date while the
    Schwab archive key is the preceding Pacific date.  Both the normalized
    session date and the decision close must agree before a label is accepted.
    """
    return price_anchored_next_session_label_from_index(
        row,
        index_schwab_daily(candles),
        round_trip_cost_pct=round_trip_cost_pct,
        close_tolerance_fraction=close_tolerance_fraction,
        maximum_next_session_gap_days=maximum_next_session_gap_days,
    )


def next_session_label(
    row: Mapping[str, Any],
    candles: Iterable[Mapping[str, Any]],
    *,
    entry_assumption: str,
    round_trip_cost_pct: float,
    maximum_calendar_gap_days: int = 5,
) -> dict[str, Any] | None:
    if entry_assumption not in {
        "same_session_close",
        "next_regular_session_open",
    }:
        raise ValueError("unsupported entry assumption")
    symbol = str(row.get("symbol") or "").upper().strip()
    market_date = str(row.get("market_date") or "")
    if not symbol or not market_date:
        raise ValueError("panel row requires symbol and market_date")
    source = list(candles)
    positions = {
        str(candle.get("date") or ""): index
        for index, candle in enumerate(source)
    }
    index = positions.get(market_date)
    if index is None or index + 1 >= len(source):
        return None
    current = source[index]
    future = source[index + 1]
    current_day = __import__("datetime").date.fromisoformat(market_date)
    future_day = __import__("datetime").date.fromisoformat(str(future["date"]))
    if (future_day - current_day).days > maximum_calendar_gap_days:
        return None
    entry_price = float(
        current["close"]
        if entry_assumption == "same_session_close"
        else future["open"]
    )
    exit_price = float(future["close"])
    if entry_price <= 0.0 or exit_price <= 0.0:
        return None
    gross = (exit_price / entry_price - 1.0) * 100.0
    return {
        **dict(row),
        "entry_assumption": entry_assumption,
        "label_entry_market_date": (
            market_date
            if entry_assumption == "same_session_close"
            else str(future["date"])
        ),
        "label_entry_price": entry_price,
        "future_market_date": str(future["date"]),
        "label_exit_price": exit_price,
        "label_forward_return_1d_gross_pct": gross,
        "label_forward_return_1d_pct": gross - round_trip_cost_pct,
        "round_trip_cost_pct": round_trip_cost_pct,
        "target_horizon_sessions": 1,
        "label_contract": (
            f"{entry_assumption}; exit next complete regular-session close"
        ),
        "research_only": True,
        "execution_enabled": False,
    }


def attach_labels(
    rows: Iterable[Mapping[str, Any]],
    daily_by_symbol: Mapping[str, Iterable[Mapping[str, Any]]],
    *,
    entry_assumption: str,
    round_trip_cost_pct: float,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    output: list[dict[str, Any]] = []
    unavailable: list[dict[str, str]] = []
    for row in rows:
        symbol = str(row.get("symbol") or "").upper().strip()
        candles = daily_by_symbol.get(symbol)
        if candles is None:
            unavailable.append(
                {"symbol": symbol, "market_date": str(row.get("market_date")), "reason": "missing_daily_history"}
            )
            continue
        labeled = next_session_label(
            row,
            candles,
            entry_assumption=entry_assumption,
            round_trip_cost_pct=round_trip_cost_pct,
        )
        if labeled is None:
            unavailable.append(
                {"symbol": symbol, "market_date": str(row.get("market_date")), "reason": "next_session_unavailable"}
            )
            continue
        output.append(labeled)
    output.sort(key=lambda item: (item["market_date"], item["symbol"]))
    return output, unavailable


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument(
        "--entry-assumption",
        choices=("same_session_close", "next_regular_session_open"),
        required=True,
    )
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()
    if args.output.exists() or args.summary.exists():
        raise FileExistsError("output and summary paths must be new")
    if args.round_trip_cost_pct < 0.0:
        raise ValueError("round-trip cost cannot be negative")

    rows = read_jsonl(args.input)
    symbols = sorted(
        {str(row.get("symbol") or "").upper().strip() for row in rows}
    )
    daily = {}
    for symbol in symbols:
        path = args.daily_dir / f"{symbol}_schwab_1d_max.csv"
        if path.exists():
            daily[symbol] = load_daily(path)
    output, unavailable = attach_labels(
        rows,
        daily,
        entry_assumption=args.entry_assumption,
        round_trip_cost_pct=args.round_trip_cost_pct,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in output:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    summary = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "source_input": str(args.input),
        "daily_dir": str(args.daily_dir),
        "entry_assumption": args.entry_assumption,
        "exit_assumption": "next_complete_regular_session_close",
        "target_horizon_sessions": 1,
        "round_trip_cost_pct": args.round_trip_cost_pct,
        "input_rows": len(rows),
        "labeled_rows": len(output),
        "unavailable_rows": len(unavailable),
        "unavailable": unavailable,
    }
    args.summary.write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
