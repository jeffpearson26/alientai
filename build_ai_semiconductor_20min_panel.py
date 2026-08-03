from __future__ import annotations

"""Attach leakage-safe intraday open-to-later-close labels to a catalyst panel."""

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from alientai_v2.features.premarket_features import build_premarket_features
from build_matched_premarket_features import index_month
from download_alpha_vantage_matched_premarket import archive_path


ROUND_TRIP_COST_PCT = 0.25
PRIOR_CLOSE_PREFIXES = ("technical_", "model_call_")
NEW_YORK = ZoneInfo("America/New_York")


@lru_cache(maxsize=64)
def schwab_rows(path_text: str) -> tuple[dict[str, Any], ...]:
    path = Path(path_text)
    if not path.exists():
        return ()
    output: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for source in csv.DictReader(handle):
            try:
                stamp = datetime.fromisoformat(str(source["datetime_utc"]))
                if stamp.tzinfo is None:
                    raise ValueError("Schwab datetime_utc must include an offset")
                stamp_et = stamp.astimezone(NEW_YORK)
            except (KeyError, TypeError, ValueError):
                continue
            output.append({
                "timestamp": stamp_et.strftime("%Y-%m-%d %H:%M:%S"),
                "open": source.get("open"),
                "high": source.get("high"),
                "low": source.get("low"),
                "close": source.get("close"),
                "volume": source.get("volume"),
            })
    return tuple(output)


def schwab_context(archive: Path, symbol: str, market_date: str) -> list[dict[str, Any]]:
    rows = schwab_rows(str(archive / f"{symbol}_schwab_5m_max.csv"))
    dates = sorted({
        str(row.get("timestamp") or "")[:10]
        for row in rows
        if str(row.get("timestamp") or "")[:10] < market_date
    })[-10:]
    allowed = set(dates) | {market_date}
    return [
        dict(row) for row in rows
        if str(row.get("timestamp") or "")[:10] in allowed
    ]


def intraday_rows(
    archive: Path, symbol: str, market_date: str, archive_source: str
) -> list[dict[str, Any]]:
    if archive_source == "schwab":
        return schwab_context(archive, symbol, market_date)
    return index_month(
        str(archive_path(archive, symbol, market_date[:7]))
    ).get(market_date, [])


def replace_premarket(
    row: dict[str, Any], candles: list[dict[str, Any]], market_date: str
) -> dict[str, Any]:
    output = {
        name: value
        for name, value in row.items()
        if not name.startswith("model_premarket_")
    }
    output.update({
        f"model_{name}": value
        for name, value in build_premarket_features(candles, market_date).items()
    })
    return output


def intraday_label(
    rows: list[Mapping[str, Any]],
    market_date: str,
    horizon_minutes: int,
    entry_time_et: str = "09:30",
) -> dict[str, Any] | None:
    if horizon_minutes <= 0 or horizon_minutes % 5:
        raise ValueError("horizon_minutes must be a positive multiple of five")
    try:
        entry_time = datetime.strptime(entry_time_et, "%H:%M")
    except ValueError as exc:
        raise ValueError("entry_time_et must use HH:MM") from exc
    if entry_time.minute % 5:
        raise ValueError("entry_time_et must align to a five-minute bar")
    by_time = {
        str(row.get("timestamp") or "")[11:16]: row
        for row in rows
        if str(row.get("timestamp") or "")[:10] == market_date
    }
    bar_count = horizon_minutes // 5
    required = tuple(
        (entry_time + timedelta(minutes=5 * index)).strftime("%H:%M")
        for index in range(bar_count)
    )
    if any(stamp not in by_time for stamp in required):
        return None
    try:
        entry = float(by_time[entry_time_et]["open"])
        exit_bar_time = required[-1]
        exit_ = float(by_time[exit_bar_time]["close"])
    except (KeyError, TypeError, ValueError):
        return None
    if entry <= 0 or exit_ <= 0:
        return None
    gross = (exit_ / entry - 1.0) * 100.0
    return {
        "label_entry_timestamp_et": f"{market_date} {entry_time_et}:00",
        "label_exit_timestamp_et": (
            entry_time + timedelta(minutes=horizon_minutes)
        ).strftime(f"{market_date} %H:%M:00"),
        f"label_entry_{entry_time_et.replace(':', '')}_open": entry,
        f"label_exit_{exit_bar_time.replace(':', '')}_close": exit_,
        f"label_forward_return_{horizon_minutes}m_gross_pct": gross,
        f"label_forward_return_{horizon_minutes}m_net_pct": gross - ROUND_TRIP_COST_PCT,
        "label_end_market_date": market_date,
    }


def twenty_minute_label(rows: list[Mapping[str, Any]], market_date: str) -> dict[str, Any] | None:
    return intraday_label(rows, market_date, 20)


def daily_calendars(daily_root: Path, symbols: set[str]) -> dict[str, list[str]]:
    output = {}
    for symbol in symbols:
        payload = json.loads((daily_root / f"{symbol}_daily.json").read_text(encoding="utf-8"))
        series = next(
            (value for key, value in payload.items() if str(key).startswith("Time Series")),
            {},
        )
        output[symbol] = sorted(series)
    return output


def shift_prior_close_features(
    rows: list[dict[str, Any]], calendars: Mapping[str, list[str]]
) -> tuple[list[dict[str, Any]], int]:
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_symbol[str(row["symbol"])].append(row)
    output, missing = [], 0
    for symbol, symbol_rows in by_symbol.items():
        indexed = {str(row["market_date"]): row for row in symbol_rows}
        calendar = calendars[symbol]
        for row in symbol_rows:
            market_date = str(row["market_date"])
            if market_date not in calendar or calendar.index(market_date) == 0:
                missing += 1
                continue
            prior_date = calendar[calendar.index(market_date) - 1]
            prior = indexed.get(prior_date)
            if prior is None:
                missing += 1
                continue
            shifted = dict(row)
            for name in list(shifted):
                if name.startswith(PRIOR_CLOSE_PREFIXES):
                    shifted.pop(name)
            shifted.update({
                name: value
                for name, value in prior.items()
                if name.startswith(PRIOR_CLOSE_PREFIXES)
            })
            shifted["prior_feature_market_date"] = prior_date
            output.append(shifted)
    return output, missing


def build(
    rows: list[dict[str, Any]], archive: Path, calendars: Mapping[str, list[str]],
    horizon_minutes: int = 20,
    entry_time_et: str = "09:30",
    archive_source: str = "alpha_vantage",
) -> tuple[list[dict[str, Any]], int]:
    if archive_source not in {"alpha_vantage", "schwab"}:
        raise ValueError("archive_source must be alpha_vantage or schwab")
    shifted_rows, missing_prior = shift_prior_close_features(rows, calendars)
    output, missing = [], missing_prior
    for row in shifted_rows:
        symbol, market_date = str(row["symbol"]), str(row["market_date"])
        month_rows = intraday_rows(archive, symbol, market_date, archive_source)
        if archive_source == "schwab":
            row = replace_premarket(row, month_rows, market_date)
        label = intraday_label(
            month_rows,
            market_date,
            horizon_minutes,
            entry_time_et,
        )
        if label is None:
            missing += 1
            continue
        output.append({
            **row,
            **label,
            "label_source": (
                "Schwab pricehistory 5min extended-hours"
                if archive_source == "schwab"
                else "Alpha Vantage TIME_SERIES_INTRADAY 5min"
            ),
            "premarket_feature_source": (
                "Schwab pricehistory 5min extended-hours"
                if archive_source == "schwab"
                else row.get("premarket_feature_source", "Alpha Vantage TIME_SERIES_INTRADAY 5min")
            ),
            "label_contract": (
                f"{entry_time_et} ET bar open to the bar close after "
                f"{horizon_minutes} elapsed minutes"
            ),
            "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
            "research_only": True,
            "execution_enabled": False,
        })
    return output, missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--daily-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--horizon-minutes", type=int, default=20)
    parser.add_argument("--entry-time-et", default="09:30")
    parser.add_argument(
        "--archive-source",
        choices=("alpha_vantage", "schwab"),
        default="alpha_vantage",
    )
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    calendars = daily_calendars(args.daily_root, {str(row["symbol"]) for row in rows})
    output, missing = build(
        rows,
        args.archive,
        calendars,
        args.horizon_minutes,
        args.entry_time_et,
        args.archive_source,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in output), encoding="utf-8")
    print(json.dumps({
        "status": "complete",
        "research_only": True,
        "rows": len(output),
        "missing_labels": missing,
        "dates": len({row["market_date"] for row in output}),
        "symbols": len({row["symbol"] for row in output}),
        "entry_time_et": args.entry_time_et,
        "archive_source": args.archive_source,
    }, indent=2))


if __name__ == "__main__":
    main()
