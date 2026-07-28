from __future__ import annotations

"""Evaluate 60-session outcomes after leakage-safe unusual call activity."""

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from alientai_v2.research.unusual_call_activity import unusual_call_features
from evaluate_context_portfolio import daily_archive_sha256, load_daily_closes
from evaluate_unusual_call_outcomes import read_jsonl


HORIZON_SESSIONS = 60
DRASTIC_GAIN_THRESHOLDS_PCT = (20.0, 30.0, 50.0)
ROUND_TRIP_COST_PCT = 0.25


def resolve_entry_day(
    path: Mapping[date, float], nominal_day: date, expected_close: float,
) -> date | None:
    candidates = [
        day for day, close in path.items()
        if abs((day - nominal_day).days) <= 3
        and abs(close / expected_close - 1.0) <= 0.00001
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda day: (abs((day - nominal_day).days), day))


def materialize_outcomes(
    base_rows: Iterable[Mapping[str, Any]],
    option_rows: Iterable[Mapping[str, Any]],
    daily_closes: Mapping[str, Mapping[date, float]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    base = {
        (str(row.get("symbol") or "").upper(), str(row.get("market_date") or "")): row
        for row in base_rows
    }
    features = unusual_call_features(option_rows)
    output = []
    counts = {
        "option_feature_rows": len(features),
        "missing_base_row": 0,
        "missing_daily_history": 0,
        "unresolved_entry_close": 0,
        "incomplete_60_session_horizon": 0,
    }
    for feature in features:
        key = (str(feature["symbol"]), str(feature["market_date"]))
        source = base.get(key)
        if source is None:
            counts["missing_base_row"] += 1
            continue
        try:
            nominal_day = date.fromisoformat(key[1])
            expected_close = float(source["close"])
            path = daily_closes[key[0]]
        except (KeyError, TypeError, ValueError):
            counts["missing_daily_history"] += 1
            continue
        entry_day = resolve_entry_day(path, nominal_day, expected_close)
        if entry_day is None:
            counts["unresolved_entry_close"] += 1
            continue
        future_days = sorted(day for day in path if day > entry_day)
        if len(future_days) < HORIZON_SESSIONS:
            counts["incomplete_60_session_horizon"] += 1
            continue
        exit_day = future_days[HORIZON_SESSIONS - 1]
        future_closes = [float(path[day]) for day in future_days[:HORIZON_SESSIONS]]
        terminal_gross = (future_closes[-1] / expected_close - 1.0) * 100.0
        maximum_gain = (max(future_closes) / expected_close - 1.0) * 100.0
        output.append({
            **feature,
            "entry_day": entry_day.isoformat(),
            "exit_day": exit_day.isoformat(),
            "terminal_gross_return_60d_pct": terminal_gross,
            "terminal_net_return_60d_pct": terminal_gross - ROUND_TRIP_COST_PCT,
            "maximum_close_gain_within_60d_pct": maximum_gain,
        })
    return output, counts


def metrics(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    if not rows:
        return {"rows": 0}
    terminal = np.asarray([float(row["terminal_net_return_60d_pct"]) for row in rows])
    maximum = np.asarray([float(row["maximum_close_gain_within_60d_pct"]) for row in rows])
    result: dict[str, Any] = {
        "rows": len(rows),
        "symbols": len({str(row["symbol"]) for row in rows}),
        "mean_terminal_net_return_pct": float(np.mean(terminal)),
        "median_terminal_net_return_pct": float(np.median(terminal)),
        "terminal_net_win_rate_pct": float(np.mean(terminal > 0.0) * 100.0),
        "mean_maximum_close_gain_pct": float(np.mean(maximum)),
        "median_maximum_close_gain_pct": float(np.median(maximum)),
    }
    for threshold in DRASTIC_GAIN_THRESHOLDS_PCT:
        result[f"terminal_gain_at_least_{threshold:g}pct_rate_pct"] = float(
            np.mean(terminal >= threshold) * 100.0
        )
        result[f"reached_{threshold:g}pct_within_60d_rate_pct"] = float(
            np.mean(maximum >= threshold) * 100.0
        )
    return result


def compare_metrics(natural: Mapping[str, Any], unusual: Mapping[str, Any]) -> dict[str, Any]:
    if not natural.get("rows") or not unusual.get("rows"):
        return {"available": False}
    output: dict[str, Any] = {
        "available": True,
        "mean_terminal_net_return_lift_pct_points": (
            float(unusual["mean_terminal_net_return_pct"])
            - float(natural["mean_terminal_net_return_pct"])
        ),
        "terminal_net_win_rate_lift_pct_points": (
            float(unusual["terminal_net_win_rate_pct"])
            - float(natural["terminal_net_win_rate_pct"])
        ),
    }
    for threshold in DRASTIC_GAIN_THRESHOLDS_PCT:
        for prefix in ("terminal_gain_at_least", "reached"):
            suffix = (
                f"{threshold:g}pct_rate_pct"
                if prefix == "terminal_gain_at_least"
                else f"{threshold:g}pct_within_60d_rate_pct"
            )
            field = f"{prefix}_{suffix}"
            output[f"{field}_lift_pct_points"] = float(unusual[field]) - float(natural[field])
    return output


def split_thirds(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    days = sorted({str(row["market_date"]) for row in rows})
    if len(days) < 3:
        return {"full_history": rows}
    first = days[len(days) // 3 - 1]
    second = days[(2 * len(days)) // 3 - 1]
    return {
        "full_history": rows,
        "early_third": [row for row in rows if str(row["market_date"]) <= first],
        "middle_third": [
            row for row in rows if first < str(row["market_date"]) <= second
        ],
        "late_third": [row for row in rows if str(row["market_date"]) > second],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-rows",
        type=Path,
        default=Path(r"D:\AlientAI\Data\FINRA_Short_Interest\features\natural_options_finra_research_panel_2026.jsonl"),
    )
    parser.add_argument(
        "--option-features",
        type=Path,
        default=Path("data_v2/rcef_research/natural_option_features_2026.jsonl"),
    )
    parser.add_argument(
        "--daily-dir",
        type=Path,
        default=Path("data_v2/sp500_daily_schwab_max_history"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data_v2/rcef_research/unusual_call_60day_outcomes_2026.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    daily_dir = root / args.daily_dir
    rows, coverage = materialize_outcomes(
        read_jsonl(args.base_rows),
        read_jsonl(root / args.option_features),
        load_daily_closes(daily_dir),
    )
    report = {
        "build": "ALIENTAI_UNUSUAL_CALL_60_SESSION_OUTCOMES_V1",
        "research_only": True,
        "execution_enabled": False,
        "unusual_call_definition": "call volume z-score at least 3 using only 10-20 strictly earlier same-symbol snapshots",
        "horizon": "60 later trading-session closes",
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        "drastic_gain_thresholds_pct": list(DRASTIC_GAIN_THRESHOLDS_PCT),
        "daily_archive_sha256": daily_archive_sha256(daily_dir),
        "coverage": coverage,
        "complete_rows": len(rows),
        "partitions": {},
    }
    for name, partition in split_thirds(rows).items():
        natural = metrics(partition)
        unusual = metrics(
            row for row in partition if row.get("call_volume_unusual") is True
        )
        report["partitions"][name] = {
            "natural_universe": natural,
            "unusual_calls": unusual,
            "unusual_call_lift": compare_metrics(natural, unusual),
        }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
