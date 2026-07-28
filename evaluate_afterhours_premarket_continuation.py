from __future__ import annotations

"""Research whether joint after-hours and premarket activity continues intraday."""

import argparse
import json
from pathlib import Path
from statistics import median
from typing import Any, Iterable

import numpy as np

from build_matched_premarket_features import index_month
from download_alpha_vantage_matched_premarket import archive_path, read_jsonl
from evaluate_selective_premarket_same_day import same_day_net_return


THRESHOLDS = (1.5, 2.0, 3.0, 5.0)
MINIMUM_CANDIDATES = 30


def afterhours_from_index(
    by_date: dict[str, list[dict[str, str]]], market_date: str,
) -> dict[str, Any]:
    """Fast indexed equivalent of the canonical feature builder."""
    prior_dates = sorted(day for day in by_date if day < market_date)
    base: dict[str, Any] = {"afterhours_available": False, "afterhours_bar_count": 0}
    if not prior_dates:
        return base
    session_day = prior_dates[-1]
    regular = [
        row for row in by_date[session_day]
        if " 09:30" <= str(row.get("timestamp") or "")[10:16] <= " 16:00"
    ]
    afterhours = [
        row for row in by_date[session_day]
        if " 16:05" <= str(row.get("timestamp") or "")[10:16] <= " 19:55"
    ]
    base.update({
        "afterhours_session_date": session_day,
        "afterhours_bar_count": len(afterhours),
        "afterhours_previous_regular_close_available": bool(regular),
    })
    if not regular or not afterhours:
        return base
    try:
        previous_close = float(regular[-1]["close"])
        first_close = float(afterhours[0]["close"])
        last_close = float(afterhours[-1]["close"])
        total_volume = sum(max(0.0, float(row.get("volume") or 0.0)) for row in afterhours)
    except (KeyError, TypeError, ValueError):
        return base
    prior_totals = []
    for day in prior_dates[:-1][-10:]:
        try:
            volume = sum(
                max(0.0, float(row.get("volume") or 0.0))
                for row in by_date[day]
                if " 16:05" <= str(row.get("timestamp") or "")[10:16] <= " 19:55"
            )
        except (TypeError, ValueError):
            continue
        if volume > 0:
            prior_totals.append(volume)
    typical_volume = median(prior_totals) if prior_totals else None
    base.update({
        "afterhours_available": True,
        "afterhours_first_close": first_close,
        "afterhours_last_close": last_close,
        "afterhours_previous_regular_close": previous_close,
        "afterhours_session_return_pct": (last_close / first_close - 1.0) * 100.0,
        "afterhours_last_vs_regular_close_pct": (last_close / previous_close - 1.0) * 100.0,
        "afterhours_volume": total_volume,
        "afterhours_typical_prior_volume": typical_volume,
        "afterhours_relative_volume": total_volume / typical_volume if typical_volume else None,
        "afterhours_last_timestamp_et": str(afterhours[-1].get("timestamp") or ""),
    })
    return base


def metrics(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    values = np.asarray([float(row["net_return_pct"]) for row in rows], dtype=float)
    if not len(values):
        return {"rows": 0, "minimum_sample_met": False}
    gross = values + 0.25
    return {
        "rows": int(len(values)),
        "minimum_sample_met": bool(len(values) >= MINIMUM_CANDIDATES),
        "gross_positive_close_rate_pct": float(np.mean(gross > 0.0) * 100.0),
        "net_win_rate_pct": float(np.mean(values > 0.0) * 100.0),
        "mean_net_return_pct": float(np.mean(values)),
        "median_net_return_pct": float(np.median(values)),
        "fifth_percentile_net_return_pct": float(np.quantile(values, 0.05)),
        "worst_net_return_pct": float(np.min(values)),
    }


def evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [
        row for row in rows
        if row.get("afterhours_available") is True
        and row.get("premarket_available") is True
        and row.get("afterhours_relative_volume") is not None
        and row.get("premarket_relative_volume") is not None
    ]
    output: dict[str, Any] = {"eligible": metrics(eligible), "fixed_thresholds": {}}
    for threshold in THRESHOLDS:
        afterhours = [
            row for row in eligible
            if float(row["afterhours_relative_volume"]) >= threshold
        ]
        premarket = [
            row for row in eligible
            if float(row["premarket_relative_volume"]) >= threshold
        ]
        joint = [
            row for row in eligible
            if float(row["afterhours_relative_volume"]) >= threshold
            and float(row["premarket_relative_volume"]) >= threshold
        ]
        output["fixed_thresholds"][f"at_least_{threshold:g}x"] = {
            "afterhours_only": metrics(afterhours),
            "premarket_only": metrics(premarket),
            "joint": metrics(joint),
        }
    return output


def build_rows(features: list[dict[str, Any]], archive: Path) -> tuple[list[dict[str, Any]], int]:
    output = []
    missing_label = 0
    for feature in features:
        symbol = str(feature.get("symbol") or "").strip().upper()
        market_date = str(feature.get("market_date") or "").strip()
        path = archive_path(archive, symbol, market_date[:7])
        by_date = index_month(str(path))
        net_return = same_day_net_return(by_date.get(market_date, []), market_date)
        if net_return is None:
            missing_label += 1
            continue
        row = dict(feature)
        row.update(afterhours_from_index(by_date, market_date))
        row["net_return_pct"] = net_return
        output.append(row)
    return output, missing_label


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
        default=Path("data_v2/rcef_research/afterhours_premarket_continuation_2026.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    features = read_jsonl(root / args.premarket_features)
    rows, missing_label = build_rows(features, args.archive)
    partitions = {
        "full_history": rows,
        "training": [row for row in rows if row["market_date"] <= "2026-04-20"],
        "validation": [row for row in rows if "2026-05-02" <= row["market_date"] <= "2026-05-26"],
        "untouched_test": [row for row in rows if row["market_date"] >= "2026-06-07"],
    }
    report = {
        "build": "ALIENTAI_AFTERHOURS_PREMARKET_CONTINUATION_V1",
        "research_only": True,
        "execution_enabled": False,
        "feature_definition": "previous completed 16:05-19:55 ET session plus current 04:00-09:25 ET session",
        "label": "same_day_0930_close_to_1600_close_minus_0.25pct_round_trip_cost",
        "feature_rows": len(features),
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
