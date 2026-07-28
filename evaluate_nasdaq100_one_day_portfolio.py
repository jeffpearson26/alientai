from __future__ import annotations

"""Validation-locked intraday portfolio evaluation for the Nasdaq one-day clone."""

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean, median
from typing import Any

import lightgbm as lgb
import numpy as np

from evaluate_nasdaq100_clone_portfolio import read_jsonl, score_rows


TARGET = "label_next_session_open_to_close_return_pct"


def select_daily(rows: list[dict[str, Any]], cutoff: float, maximum: int = 5) -> list[dict[str, Any]]:
    grouped = defaultdict(list)
    for row in rows:
        if float(row["technical_context_score"]) >= cutoff:
            grouped[str(row["label_entry_market_date"])].append(row)
    return [
        row
        for day in sorted(grouped)
        for row in sorted(grouped[day], key=lambda item: -float(item["technical_context_score"]))[:maximum]
    ]


def metrics(rows: list[dict[str, Any]], cost: float, slots: int = 5) -> dict[str, Any]:
    values = [float(row[TARGET]) - cost for row in rows]
    by_day = defaultdict(list)
    for row, value in zip(rows, values):
        by_day[str(row["label_entry_market_date"])].append(value)
    equity = peak = 1.0
    worst = 0.0
    for day in sorted(by_day):
        equity *= 1.0 + (sum(by_day[day]) / slots) / 100.0
        peak = max(peak, equity)
        worst = min(worst, (equity / peak - 1.0) * 100.0)
    return {
        "signals": len(values),
        "trading_days": len(by_day),
        "mean_net_return_pct": round(mean(values), 6) if values else None,
        "median_net_return_pct": round(median(values), 6) if values else None,
        "net_win_rate_pct": round(100 * sum(value > 0 for value in values) / len(values), 6) if values else None,
        "capital_scaled_return_pct": round((equity - 1.0) * 100.0, 6),
        "capital_scaled_max_drawdown_pct": round(worst, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--training-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fractions", type=float, nargs="+", default=[0.0025, 0.005, 0.01])
    parser.add_argument("--minimum-validation-signals", type=int, default=20)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()
    report = json.loads(args.training_report.read_text(encoding="utf-8"))
    model = lgb.Booster(model_file=str(args.model))
    scored = score_rows(read_jsonl(args.rows), model, report["feature_names"])
    validation = [row for row in scored if report["split"]["validation_start"] <= row["market_date"] <= report["split"]["validation_end"]]
    test = [row for row in scored if row["market_date"] >= report["split"]["test_start"]]
    validation_scores = np.asarray([float(row["technical_context_score"]) for row in validation])
    diagnostics = []
    for fraction in args.fractions:
        cutoff = float(np.quantile(validation_scores, 1.0 - fraction))
        selected = select_daily(validation, cutoff)
        diagnostics.append({"fraction": fraction, "cutoff": cutoff, **metrics(selected, args.round_trip_cost_pct)})
    eligible = [row for row in diagnostics if row["signals"] >= args.minimum_validation_signals]
    if not eligible:
        raise ValueError("no fraction meets the validation sample minimum")
    winner = max(eligible, key=lambda row: (row["mean_net_return_pct"], -row["fraction"]))
    test_selected = select_daily(test, winner["cutoff"])
    output = {
        "status": "complete", "research_only": True, "execution_enabled": False,
        "timing": "decide after close; enter next session open; exit same session close",
        "validation_diagnostics": diagnostics,
        "selected_fraction": winner["fraction"], "locked_score_cutoff": winner["cutoff"],
        "test": metrics(test_selected, args.round_trip_cost_pct),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
