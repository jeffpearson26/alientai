from __future__ import annotations

"""Report frozen score-percentile baskets for research, never trading decisions."""

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from evaluate_context_portfolio import capacity_limited, file_sha256
from evaluate_nasdaq100_clone_portfolio import read_jsonl, score_rows, trade_metrics


DEFAULT_PERCENTILE_EDGES = (0, 50, 60, 70, 80, 90, 100)


def percentile_edges(values: Sequence[float], edges: Sequence[int]) -> dict[int, float]:
    if not values:
        raise ValueError("validation scores are required")
    if len(edges) < 2 or edges[0] != 0 or edges[-1] != 100:
        raise ValueError("percentile edges must start at 0 and end at 100")
    if any(left >= right for left, right in zip(edges, edges[1:])):
        raise ValueError("percentile edges must be strictly increasing")
    return {edge: float(np.quantile(values, edge / 100.0)) for edge in edges}


def rows_in_basket(
    rows: Sequence[Mapping[str, Any]],
    lower_score: float,
    upper_score: float,
    includes_upper: bool,
) -> list[dict[str, Any]]:
    if includes_upper:
        return [dict(row) for row in rows if lower_score <= float(row["technical_context_score"]) <= upper_score]
    return [dict(row) for row in rows if lower_score <= float(row["technical_context_score"]) < upper_score]


def basket_report(
    rows: Sequence[Mapping[str, Any]],
    frozen_edges: Mapping[int, float],
    percentile_edges_list: Sequence[int],
    cost_pct: float,
    max_open_positions: int,
    label_field: str,
) -> list[dict[str, Any]]:
    report = []
    for lower, upper in zip(percentile_edges_list, percentile_edges_list[1:]):
        raw = rows_in_basket(
            rows,
            frozen_edges[lower],
            frozen_edges[upper],
            includes_upper=upper == percentile_edges_list[-1],
        )
        selected = capacity_limited(raw, max_open_positions)
        report.append({
            "score_percentile_basket": f"{lower}-{upper}",
            "lower_score_inclusive": round(frozen_edges[lower], 12),
            "upper_score": round(frozen_edges[upper], 12),
            "upper_score_inclusive": upper == percentile_edges_list[-1],
            "candidates_before_capacity": len(raw),
            **trade_metrics(selected, cost_pct, label_field),
        })
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Frozen validation score-percentile basket report (research only).")
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--training-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--percentile-edges", type=int, nargs="+", default=DEFAULT_PERCENTILE_EDGES)
    parser.add_argument("--max-open-positions", type=int, default=5)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()

    report = json.loads(args.training_report.read_text(encoding="utf-8"))
    label_field = str(report.get("target") or "label_forward_return_5d_pct")
    rows = read_jsonl(args.rows)
    model = lgb.Booster(model_file=str(args.model))
    scored = score_rows(rows, model, report["feature_names"])
    split = report["split"]
    validation = [
        row for row in scored
        if split["validation_start"] <= row["market_date"] <= split["validation_end"]
    ]
    test = [row for row in scored if row["market_date"] >= split["test_start"]]
    frozen_edges = percentile_edges(
        [float(row["technical_context_score"]) for row in validation],
        args.percentile_edges,
    )
    result = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "warning": "Baskets are frozen from validation score percentiles, not calibrated probabilities or trading instructions.",
        "selection_contract": "No basket is selected from later test outcomes.",
        "label_return_field": label_field,
        "horizon_sessions": sorted({int(row["holding_sessions"]) for row in rows if row.get("holding_sessions") is not None}),
        "artifacts": {
            "rows_sha256": file_sha256(args.rows),
            "model_sha256": file_sha256(args.model),
            "training_report_sha256": file_sha256(args.training_report),
        },
        "settings": {
            "percentile_edges": args.percentile_edges,
            "max_open_positions": args.max_open_positions,
            "round_trip_cost_pct": args.round_trip_cost_pct,
        },
        "split": split,
        "validation_score_percentile_cutoffs": {str(key): round(value, 12) for key, value in frozen_edges.items()},
        "validation_baskets": basket_report(validation, frozen_edges, args.percentile_edges, args.round_trip_cost_pct, args.max_open_positions, label_field),
        "later_test_baskets": basket_report(test, frozen_edges, args.percentile_edges, args.round_trip_cost_pct, args.max_open_positions, label_field),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
