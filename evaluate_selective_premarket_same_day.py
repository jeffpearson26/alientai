from __future__ import annotations

"""Test whether a 09:25 ET premarket move continues through the same session."""

import argparse
import json
from pathlib import Path
from typing import Any

from build_matched_premarket_features import index_month
from download_alpha_vantage_matched_premarket import archive_path, read_jsonl
from evaluate_selective_premarket_continuation import evaluate


ROUND_TRIP_COST_PCT = 0.25


def same_day_net_return(rows: list[dict[str, Any]], market_date: str) -> float | None:
    regular = [
        row for row in rows
        if str(row.get("timestamp") or "")[:10] == market_date
        and " 09:30" <= str(row.get("timestamp") or "")[10:16] <= " 16:00"
    ]
    regular.sort(key=lambda row: str(row.get("timestamp") or ""))
    if not regular:
        return None
    if str(regular[0].get("timestamp") or "")[10:16] != " 09:30":
        return None
    if str(regular[-1].get("timestamp") or "")[10:16] != " 16:00":
        return None
    try:
        entry = float(regular[0]["close"])
        exit_ = float(regular[-1]["close"])
    except (KeyError, TypeError, ValueError):
        return None
    if entry <= 0 or exit_ <= 0:
        return None
    return (exit_ / entry - 1.0) * 100.0 - ROUND_TRIP_COST_PCT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--premarket-features",
        type=Path,
        default=Path("data_v2/rcef_research/selective_natural_premarket_features_2026.jsonl"),
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path(r"D:\AlientAI\Data\AlphaVantage_2026\selective_natural_premarket_5min_2026"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data_v2/rcef_research/selective_premarket_same_day_2026.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent

    rows = []
    missing_label = 0
    for feature in read_jsonl(root / args.premarket_features):
        symbol = str(feature.get("symbol") or "")
        market_date = str(feature.get("market_date") or "")
        path = archive_path(args.archive, symbol, market_date[:7])
        net_return = same_day_net_return(index_month(str(path)).get(market_date, []), market_date)
        if net_return is None:
            missing_label += 1
            continue
        row = dict(feature)
        row["net_return_pct"] = net_return
        rows.append(row)

    partitions = {
        "full_history": rows,
        "training": [row for row in rows if row["market_date"] <= "2026-04-20"],
        "validation": [row for row in rows if "2026-05-02" <= row["market_date"] <= "2026-05-26"],
        "untouched_test": [row for row in rows if row["market_date"] >= "2026-06-07"],
    }
    report = {
        "build": "ALIENTAI_SELECTIVE_PREMARKET_SAME_DAY_V1",
        "research_only": True,
        "execution_enabled": False,
        "label": "first_0930_regular_5min_bar_close_to_1600_bar_close_minus_0.25pct_cost",
        "feature_rows": len(rows) + missing_label,
        "labeled_rows": len(rows),
        "excluded_nonstandard_or_missing_session": missing_label,
        "partitions": {name: evaluate(partition) for name, partition in partitions.items()},
    }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
