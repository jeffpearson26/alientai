from __future__ import annotations

"""Validation-locked, capital-scaled evaluation of the Nasdaq-100 clone."""

import argparse
import json
from datetime import date
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from evaluate_context_portfolio import (
    capital_scaled_drawdown,
    capacity_limited,
    daily_archive_sha256,
    file_sha256,
    load_daily_bars,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def score_rows(
    rows: Sequence[Mapping[str, Any]],
    model: lgb.Booster,
    feature_names: Sequence[str],
) -> list[dict[str, Any]]:
    matrix = np.asarray(
        [[float(row.get(name) or 0.0) for name in feature_names] for row in rows],
        dtype=np.float32,
    )
    scores = model.predict(matrix, num_iteration=model.best_iteration)
    return [{**row, "technical_context_score": float(score)} for row, score in zip(rows, scores)]


def trade_metrics(rows: Sequence[Mapping[str, Any]], cost_pct: float) -> dict[str, Any]:
    values = [float(row["label_forward_return_5d_pct"]) - cost_pct for row in rows]
    if not values:
        return {"signals": 0, "mean_net_return_pct": None, "median_net_return_pct": None, "net_win_rate_pct": None}
    return {
        "signals": len(values),
        "mean_net_return_pct": round(mean(values), 6),
        "median_net_return_pct": round(median(values), 6),
        "net_win_rate_pct": round(100.0 * sum(value > 0 for value in values) / len(values), 6),
    }


def select_validation_fraction(
    validation: Sequence[Mapping[str, Any]],
    fractions: Sequence[float],
    minimum_signals: int,
    cost_pct: float,
    minimum_mean_net_return_pct: float = 0.0,
    minimum_median_net_return_pct: float = 0.0,
    minimum_net_win_rate_pct: float = 50.0,
) -> tuple[float, float, list[dict[str, Any]]]:
    scores = np.asarray([float(row["technical_context_score"]) for row in validation])
    candidates = []
    for fraction in fractions:
        cutoff = float(np.quantile(scores, 1.0 - fraction))
        selected = [row for row in validation if float(row["technical_context_score"]) >= cutoff]
        metrics = trade_metrics(selected, cost_pct)
        candidates.append({"fraction": fraction, "cutoff": cutoff, **metrics})
    eligible = [
        row for row in candidates
        if row["signals"] >= minimum_signals
        and row["mean_net_return_pct"] is not None
        and row["median_net_return_pct"] is not None
        and row["net_win_rate_pct"] is not None
        and row["mean_net_return_pct"] > minimum_mean_net_return_pct
        and row["median_net_return_pct"] > minimum_median_net_return_pct
        and row["net_win_rate_pct"] >= minimum_net_win_rate_pct
    ]
    if not eligible:
        raise ValueError("no validation fraction meets the locked quality gates")
    winner = max(eligible, key=lambda row: (row["mean_net_return_pct"], -row["fraction"]))
    return float(winner["fraction"]), float(winner["cutoff"]), candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--training-report", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fractions", type=float, nargs="+", default=[0.0025, 0.005, 0.01])
    parser.add_argument("--minimum-validation-signals", type=int, default=20)
    parser.add_argument("--max-open-positions", type=int, default=5)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    parser.add_argument("--minimum-mean-net-return-pct", type=float, default=0.0)
    parser.add_argument("--minimum-median-net-return-pct", type=float, default=0.0)
    parser.add_argument("--minimum-net-win-rate-pct", type=float, default=50.0)
    args = parser.parse_args()

    report = json.loads(args.training_report.read_text(encoding="utf-8"))
    rows = read_jsonl(args.rows)
    model = lgb.Booster(model_file=str(args.model))
    scored = score_rows(rows, model, report["feature_names"])
    validation_start = date.fromisoformat(report["split"]["validation_start"])
    validation_end = date.fromisoformat(report["split"]["validation_end"])
    test_start = date.fromisoformat(report["split"]["test_start"])
    validation = [
        row for row in scored
        if validation_start <= date.fromisoformat(row["market_date"]) <= validation_end
    ]
    test = [row for row in scored if date.fromisoformat(row["market_date"]) >= test_start]
    fraction, cutoff, diagnostics = select_validation_fraction(
        validation, args.fractions, args.minimum_validation_signals, args.round_trip_cost_pct,
        args.minimum_mean_net_return_pct, args.minimum_median_net_return_pct,
        args.minimum_net_win_rate_pct,
    )
    test_candidates = [row for row in test if float(row["technical_context_score"]) >= cutoff]
    selected = capacity_limited(test_candidates, args.max_open_positions)
    daily_closes = load_daily_bars(args.daily_dir)
    result = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "selection_contract": "fraction and score cutoff selected using validation only; test evaluated once",
        "artifacts": {
            "rows_sha256": file_sha256(args.rows),
            "model_sha256": file_sha256(args.model),
            "training_report_sha256": file_sha256(args.training_report),
            "daily_archive_sha256": daily_archive_sha256(args.daily_dir),
        },
        "settings": {
            "candidate_fractions": args.fractions,
            "minimum_validation_signals": args.minimum_validation_signals,
            "max_open_positions": args.max_open_positions,
            "round_trip_cost_pct": args.round_trip_cost_pct,
            "minimum_mean_net_return_pct": args.minimum_mean_net_return_pct,
            "minimum_median_net_return_pct": args.minimum_median_net_return_pct,
            "minimum_net_win_rate_pct": args.minimum_net_win_rate_pct,
        },
        "validation_diagnostics": diagnostics,
        "selected_fraction": fraction,
        "locked_score_cutoff": cutoff,
        "test_candidates_before_capacity": len(test_candidates),
        "test": {
            **trade_metrics(selected, args.round_trip_cost_pct),
            **capital_scaled_drawdown(
                selected, daily_closes, args.max_open_positions, args.round_trip_cost_pct,
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
