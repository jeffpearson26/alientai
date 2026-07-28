from __future__ import annotations

"""Validation-locked five-slot evaluation of the Nasdaq 10-session clone."""

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from statistics import mean, median
from typing import Any

import lightgbm as lgb
import numpy as np

from evaluate_nasdaq100_clone_portfolio import read_jsonl, score_rows


TARGET = "label_10_session_open_to_close_return_pct"


def select_capacity(rows: list[dict[str, Any]], cutoff: float, slots: int = 5) -> list[dict[str, Any]]:
    active_exits: list[date] = []
    selected = []
    for row in sorted(rows, key=lambda item: (item["label_entry_market_date"], -float(item["technical_context_score"]))):
        entry = date.fromisoformat(row["label_entry_market_date"])
        active_exits = [exit_day for exit_day in active_exits if entry <= exit_day]
        if float(row["technical_context_score"]) < cutoff or len(active_exits) >= slots:
            continue
        exit_day = date.fromisoformat(row["label_exit_market_date"])
        if exit_day <= entry:
            continue
        selected.append(row)
        active_exits.append(exit_day)
    return selected


def load_closes(directory: Path, symbols: set[str]) -> dict[str, dict[date, float]]:
    output = {}
    for symbol in symbols:
        path = directory / f"{symbol}_schwab_1d_max.csv"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", newline="") as handle:
            output[symbol] = {
                date.fromisoformat(row["date"]): float(row["close"])
                for row in csv.DictReader(handle)
                if row.get("date") and row.get("close")
            }
    return output


def portfolio_metrics(rows: list[dict[str, Any]], closes: dict[str, dict[date, float]], cost: float, slots: int = 5) -> dict[str, Any]:
    net_returns = [float(row[TARGET]) - cost for row in rows]
    trades = [{
        "symbol": row["symbol"],
        "entry": date.fromisoformat(row["label_entry_market_date"]),
        "exit": date.fromisoformat(row["label_exit_market_date"]),
        "entry_price": float(row["label_entry_open"]),
        "exit_price": float(row["label_exit_close"]),
    } for row in rows]
    if not trades:
        raise ValueError("no selected trades")
    all_days = sorted({
        day for trade in trades for day in closes[trade["symbol"]]
        if trade["entry"] <= day <= trade["exit"]
    })
    cash, equity, peak, worst = 1.0, 1.0, 1.0, 0.0
    active = []
    entries = {}
    for trade in trades:
        entries.setdefault(trade["entry"], []).append(trade)
    for day in all_days:
        for position in active:
            if day in closes[position["symbol"]]:
                position["last_price"] = closes[position["symbol"]][day]
        for position in list(active):
            if position["exit"] == day:
                cash += position["shares"] * position["exit_price"] * (1.0 - cost / 100.0)
                active.remove(position)
        marked = cash + sum(position["shares"] * position["last_price"] for position in active)
        for trade in entries.get(day, []):
            if len(active) >= slots:
                raise ValueError("selected trades violate capacity")
            allocation = min(cash, marked / slots)
            cash -= allocation
            active.append({**trade, "shares": allocation / trade["entry_price"], "last_price": trade["entry_price"]})
        equity = cash + sum(position["shares"] * position["last_price"] for position in active)
        peak = max(peak, equity)
        worst = min(worst, (equity / peak - 1.0) * 100.0)
    return {
        "signals": len(rows),
        "mean_net_return_pct": round(mean(net_returns), 6),
        "median_net_return_pct": round(median(net_returns), 6),
        "net_win_rate_pct": round(100 * sum(value > 0 for value in net_returns) / len(net_returns), 6),
        "capital_scaled_return_pct": round((equity - 1.0) * 100.0, 6),
        "capital_scaled_max_drawdown_pct": round(worst, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--training-report", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
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
    closes = load_closes(args.daily_dir, {row["symbol"] for row in scored})
    validation_scores = np.asarray([float(row["technical_context_score"]) for row in validation])
    diagnostics = []
    for fraction in args.fractions:
        cutoff = float(np.quantile(validation_scores, 1.0 - fraction))
        selected = select_capacity(validation, cutoff)
        diagnostics.append({"fraction": fraction, "cutoff": cutoff, **portfolio_metrics(selected, closes, args.round_trip_cost_pct)})
    eligible = [row for row in diagnostics if row["signals"] >= args.minimum_validation_signals]
    if not eligible:
        raise ValueError("no validation fraction meets minimum sample")
    winner = max(eligible, key=lambda row: (row["mean_net_return_pct"], -row["fraction"]))
    selected_test = select_capacity(test, winner["cutoff"])
    output = {
        "status": "complete", "research_only": True, "execution_enabled": False,
        "timing": "decide after close; enter next-session open; exit tenth-session close",
        "validation_diagnostics": diagnostics,
        "selected_fraction": winner["fraction"], "locked_score_cutoff": winner["cutoff"],
        "test": portfolio_metrics(selected_test, closes, args.round_trip_cost_pct),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
