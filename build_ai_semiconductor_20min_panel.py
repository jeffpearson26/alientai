from __future__ import annotations

"""Attach leakage-safe 09:30-open to 09:45-close labels to a catalyst panel."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from build_matched_premarket_features import index_month
from download_alpha_vantage_matched_premarket import archive_path


ROUND_TRIP_COST_PCT = 0.25
PRIOR_CLOSE_PREFIXES = ("technical_", "model_call_")


def twenty_minute_label(rows: list[Mapping[str, Any]], market_date: str) -> dict[str, Any] | None:
    by_time = {
        str(row.get("timestamp") or "")[11:16]: row
        for row in rows
        if str(row.get("timestamp") or "")[:10] == market_date
    }
    required = ("09:30", "09:35", "09:40", "09:45")
    if any(stamp not in by_time for stamp in required):
        return None
    try:
        entry = float(by_time["09:30"]["open"])
        exit_ = float(by_time["09:45"]["close"])
    except (KeyError, TypeError, ValueError):
        return None
    if entry <= 0 or exit_ <= 0:
        return None
    gross = (exit_ / entry - 1.0) * 100.0
    return {
        "label_entry_timestamp_et": f"{market_date} 09:30:00",
        "label_exit_timestamp_et": f"{market_date} 09:50:00",
        "label_entry_0930_open": entry,
        "label_exit_0945_close": exit_,
        "label_forward_return_20m_gross_pct": gross,
        "label_forward_return_20m_net_pct": gross - ROUND_TRIP_COST_PCT,
        "label_end_market_date": market_date,
    }


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
    rows: list[dict[str, Any]], archive: Path, calendars: Mapping[str, list[str]]
) -> tuple[list[dict[str, Any]], int]:
    shifted_rows, missing_prior = shift_prior_close_features(rows, calendars)
    output, missing = [], missing_prior
    for row in shifted_rows:
        symbol, market_date = str(row["symbol"]), str(row["market_date"])
        month_rows = index_month(str(archive_path(archive, symbol, market_date[:7]))).get(market_date, [])
        label = twenty_minute_label(month_rows, market_date)
        if label is None:
            missing += 1
            continue
        output.append({
            **row,
            **label,
            "label_source": "Alpha Vantage TIME_SERIES_INTRADAY 5min",
            "label_contract": "09:30 ET bar open to 09:45 ET bar close (20 elapsed minutes)",
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
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    calendars = daily_calendars(args.daily_root, {str(row["symbol"]) for row in rows})
    output, missing = build(rows, args.archive, calendars)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in output), encoding="utf-8")
    print(json.dumps({
        "status": "complete",
        "research_only": True,
        "rows": len(output),
        "missing_labels": missing,
        "dates": len({row["market_date"] for row in output}),
        "symbols": len({row["symbol"] for row in output}),
    }, indent=2))


if __name__ == "__main__":
    main()
