from __future__ import annotations

"""Evaluate same-day reactions to explicit, premarket analyst upgrades."""

import argparse
import csv
import gzip
import json
from datetime import datetime, time
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo


EASTERN = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


def load_explicit_events(path: Path) -> list[dict[str, Any]]:
    output = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            document = json.loads(line)
            row = document.get("normalized") or document
            raw = row.get("raw_payload") or {}
            if raw.get("parse_quality") == "explicit_old_to_new":
                output.append(row)
    return output


def load_daily_ohlc(directory: Path) -> dict[str, list[dict[str, Any]]]:
    output = {}
    for path in directory.glob("*_schwab_1d_max.csv"):
        rows = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            for source in csv.DictReader(handle):
                try:
                    rows.append({
                        "date": str(source["date"]),
                        "open": float(source["open"]),
                        "close": float(source["close"]),
                    })
                except (KeyError, TypeError, ValueError):
                    continue
        if rows:
            output[path.name.split("_schwab_", 1)[0].upper()] = sorted(
                rows, key=lambda row: row["date"]
            )
    return output


def event_session(timestamp: str) -> tuple[str, str]:
    stamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(EASTERN)
    if stamp.time() < time(9, 30):
        session = "premarket"
    elif stamp.time() <= time(16, 0):
        session = "intraday"
    else:
        session = "afterhours"
    return stamp.date().isoformat(), session


def evaluate_events(
    events: Iterable[Mapping[str, Any]],
    histories: Mapping[str, list[Mapping[str, Any]]],
    old_rating: str,
    new_rating: str,
) -> dict[str, Any]:
    exact = [
        row for row in events
        if str(row.get("old_rating") or "").strip().casefold() == old_rating.casefold()
        and str(row.get("new_rating") or "").strip().casefold() == new_rating.casefold()
    ]
    sessions = {"premarket": 0, "intraday": 0, "afterhours": 0}
    missing_history = 0
    # Multiple firms may act on one ticker on one day. Count the price outcome
    # once per symbol-day so it is not duplicated.
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for event in exact:
        try:
            market_date, session = event_session(str(event["announcement_timestamp_utc"]))
        except (KeyError, ValueError):
            continue
        sessions[session] += 1
        if session != "premarket":
            continue
        symbol = str(event.get("ticker") or "").upper()
        history = histories.get(symbol)
        if not history:
            missing_history += 1
            continue
        index = next((i for i, row in enumerate(history) if row["date"] == market_date), None)
        if index is None or index < 1:
            missing_history += 1
            continue
        current = history[index]
        prior = history[index - 1]
        baseline = history[max(0, index - 20):index]
        if not baseline:
            continue
        open_to_close = (float(current["close"]) / float(current["open"]) - 1.0) * 100.0
        previous_to_close = (float(current["close"]) / float(prior["close"]) - 1.0) * 100.0
        gap = (float(current["open"]) / float(prior["close"]) - 1.0) * 100.0
        prior_open_close = [
            (float(row["close"]) / float(row["open"]) - 1.0) * 100.0 for row in baseline
        ]
        unique[(symbol, market_date)] = {
            "open_to_close_pct": open_to_close,
            "previous_close_to_close_pct": previous_to_close,
            "opening_gap_pct": gap,
            "open_to_close_excess_vs_prior20_mean_pct": open_to_close - mean(prior_open_close),
        }
    rows = list(unique.values())

    def summary(field: str) -> dict[str, float | int]:
        values = [float(row[field]) for row in rows]
        if not values:
            return {"rows": 0}
        return {
            "rows": len(values),
            "mean_pct": mean(values),
            "median_pct": median(values),
            "positive_rate_pct": sum(value > 0 for value in values) / len(values) * 100.0,
        }

    return {
        "old_rating": old_rating,
        "new_rating": new_rating,
        "exact_event_count": len(exact),
        "announcement_sessions": sessions,
        "unique_premarket_symbol_days_with_prices": len(rows),
        "missing_or_nontrading_daily_history": missing_history,
        "opening_gap": summary("opening_gap_pct"),
        "open_to_close": summary("open_to_close_pct"),
        "previous_close_to_close": summary("previous_close_to_close_pct"),
        "open_to_close_excess_vs_prior20_mean": summary(
            "open_to_close_excess_vs_prior20_mean_pct"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--events",
        type=Path,
        default=Path("data_v2/analyst_ratings_kaggle_history/parsed_rating_events.jsonl.gz"),
    )
    parser.add_argument(
        "--daily-dir",
        type=Path,
        default=Path("data_v2/sp500_daily_schwab_max_history"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data_v2/rcef_research/analyst_upgrade_same_day.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    events = load_explicit_events(root / args.events)
    histories = load_daily_ohlc(root / args.daily_dir)
    report = {
        "build": "ALIENTAI_ANALYST_UPGRADE_SAME_DAY_V1",
        "research_only": True,
        "execution_enabled": False,
        "source_warning": "Unofficial Kaggle mirror of historical Benzinga headlines; explicit old-to-new events only.",
        "timing_policy": "Return metrics use only announcements timestamped before 09:30 America/New_York.",
        "explicit_events_loaded": len(events),
        "hold_to_strong_buy": evaluate_events(events, histories, "Hold", "Strong Buy"),
        "hold_to_buy": evaluate_events(events, histories, "Hold", "Buy"),
    }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
