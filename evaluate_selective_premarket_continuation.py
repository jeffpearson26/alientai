from __future__ import annotations

"""Evaluate whether natural-universe premarket movers continue over five sessions."""

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from train_selective_five_day_challenger import materialize_panel, read_jsonl


THRESHOLDS = (0.0, 1.0, 2.0, 3.0, 5.0)


def metrics(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    values = np.asarray([float(row["net_return_pct"]) for row in rows], dtype=float)
    if not len(values):
        return {"rows": 0}
    return {
        "rows": int(len(values)),
        "win_rate_pct": float(np.mean(values > 0.0) * 100.0),
        "mean_net_return_pct": float(np.mean(values)),
        "median_net_return_pct": float(np.median(values)),
        "large_gain_5pct_rate_pct": float(np.mean(values >= 5.0) * 100.0),
        "large_loss_5pct_rate_pct": float(np.mean(values <= -5.0) * 100.0),
        "fifth_percentile_net_return_pct": float(np.quantile(values, 0.05)),
    }


def evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    available = [
        row for row in rows
        if row.get("premarket_available") is True and row.get("premarket_gap_pct") is not None
    ]
    output: dict[str, Any] = {"all_available": metrics(available), "positive_gap_thresholds": {}}
    for threshold in THRESHOLDS:
        selected = [row for row in available if float(row["premarket_gap_pct"]) >= threshold]
        output["positive_gap_thresholds"][f"at_least_{threshold:g}pct"] = metrics(selected)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-panel",
        type=Path,
        default=Path(r"D:\AlientAI\Data\FINRA_Short_Interest\features\natural_options_finra_research_panel_2026.jsonl"),
    )
    parser.add_argument(
        "--premarket-features",
        type=Path,
        default=Path("data_v2/rcef_research/selective_natural_premarket_features_2026.jsonl"),
    )
    parser.add_argument("--daily-dir", type=Path, default=Path("data_v2/sp500_daily_schwab_max_history"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data_v2/rcef_research/selective_premarket_continuation_2026.json"),
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    base, coverage = materialize_panel(read_jsonl(args.input_panel), root / args.daily_dir)
    premarket = {
        (str(row["symbol"]), str(row["market_date"])): row
        for row in read_jsonl(root / args.premarket_features)
    }
    joined = []
    for source in base:
        row = dict(source)
        row.update(premarket[(str(row["symbol"]), str(row["market_date"]))])
        joined.append(row)

    partitions = {
        "full_history": joined,
        "training": [row for row in joined if row["market_date"] <= "2026-04-20"],
        "validation": [row for row in joined if "2026-05-02" <= row["market_date"] <= "2026-05-26"],
        "untouched_test": [row for row in joined if row["market_date"] >= "2026-06-07"],
    }
    report = {
        "build": "ALIENTAI_SELECTIVE_PREMARKET_CONTINUATION_V1",
        "research_only": True,
        "execution_enabled": False,
        "label": "next_regular_session_open_to_fifth_session_close_minus_0.25pct_round_trip_cost",
        "coverage": coverage,
        "premarket_rows": len(premarket),
        "partitions": {name: evaluate(rows) for name, rows in partitions.items()},
    }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
