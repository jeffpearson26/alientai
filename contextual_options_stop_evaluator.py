"""Research-only stop-loss evaluation for the contextual unusual-call portfolio."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.research.rare_signal_gate import evaluate_rare_signal_gate
from evaluate_context_portfolio import capacity_limited, file_sha256, split_chronologically
from evaluate_matched_winner_full_universe import selection_metrics
from evaluate_unusual_call_contexts import score_rows
from evaluate_unusual_call_outcomes import join_option_outcomes, read_jsonl


def number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"expected number, received {value!r}") from exc


def load_daily_paths(directory: Path) -> Dict[str, list[Dict[str, Any]]]:
    paths: Dict[str, list[Dict[str, Any]]] = {}
    for path in sorted(directory.glob("*_schwab_1d_max.csv")):
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            continue
        symbol = str(rows[0].get("symbol") or "").strip().upper()
        if not symbol:
            continue
        paths[symbol] = sorted(rows, key=lambda row: str(row.get("date") or ""))
    if not paths:
        raise ValueError("daily directory contains no usable Schwab history files")
    return paths


def stopped_return(row: Mapping[str, Any], path: Sequence[Mapping[str, Any]], stop_loss_pct: float) -> Dict[str, Any] | None:
    if not stop_loss_pct < 0:
        raise ValueError("stop_loss_pct must be negative")
    decision = str(row.get("market_date") or "")
    target = str(row.get("future_market_date") or "")
    entry = number(row.get("close"))
    if entry <= 0 or not decision or not target:
        return None
    future = [item for item in path if decision < str(item.get("date") or "") <= target]
    if len(future) != 5:
        return None
    stop_price = entry * (1.0 + stop_loss_pct / 100.0)
    for item in future:
        open_price, low_price = number(item.get("open")), number(item.get("low"))
        item_date = str(item.get("date") or "")
        if open_price <= stop_price:
            return {"return_pct": round((open_price / entry - 1.0) * 100.0, 6), "exit_date": item_date, "stopped": True}
        if low_price <= stop_price:
            return {"return_pct": round(stop_loss_pct, 6), "exit_date": item_date, "stopped": True}
    final_close = number(future[-1].get("close"))
    return {"return_pct": round((final_close / entry - 1.0) * 100.0, 6), "exit_date": str(future[-1].get("date") or ""), "stopped": False}


def select_with_stop(
    calibration: Sequence[Mapping[str, Any]], test: Sequence[Mapping[str, Any]], paths: Mapping[str, Sequence[Mapping[str, Any]]],
    top_fraction: float, stop_loss_pct: float, max_open_positions: int, round_trip_cost_pct: float,
) -> Dict[str, Any]:
    scores = np.asarray([number(row["technical_context_score"]) for row in calibration], dtype=float)
    cutoff = float(np.quantile(scores, 1.0 - top_fraction))
    candidates = [row for row in test if row.get("call_volume_unusual") and number(row["technical_context_score"]) >= cutoff]
    # Retain the original five-session capacity constraint.  Allowing early stop exits
    # to create extra entries would otherwise make the stop comparison optimistic.
    selected = capacity_limited(candidates, max_open_positions)
    stopped_rows = []
    skipped = 0
    for row in selected:
        outcome = stopped_return(row, paths.get(str(row.get("symbol") or "").upper(), []), stop_loss_pct)
        if outcome is None:
            skipped += 1
            continue
        stopped_rows.append({
            **row,
            "label_forward_return_5d_pct": outcome["return_pct"],
            "future_market_date": outcome["exit_date"],
            "stop_triggered": outcome["stopped"],
        })
    metrics = selection_metrics(stopped_rows, round_trip_cost_pct)
    return {
        "technical_top_fraction_selected_on_calibration": top_fraction,
        "technical_score_cutoff_from_calibration": cutoff,
        "stop_loss_pct": stop_loss_pct,
        "test_unusual_call_candidates": len(candidates),
        "selected_before_price_path_check": len(selected),
        "skipped_missing_complete_price_path": skipped,
        "stop_triggered_signals": sum(item["stop_triggered"] for item in stopped_rows),
        "max_open_positions": max_open_positions,
        **metrics,
        "rare_signal_gate": evaluate_rare_signal_gate(metrics),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-rows", type=Path, required=True)
    parser.add_argument("--option-features", type=Path, required=True)
    parser.add_argument("--technical-model", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--calibration-fraction", type=float, default=0.50)
    parser.add_argument("--embargo-calendar-days", type=int, default=7)
    parser.add_argument("--max-open-positions", type=int, default=5)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    parser.add_argument("--stop-loss-pct", type=float, action="append", required=True)
    args = parser.parse_args()
    raw_rows = join_option_outcomes(read_jsonl(args.base_rows), read_jsonl(args.option_features))
    model = lgb.Booster(model_file=str(args.technical_model))
    rows = score_rows(raw_rows, model)
    calibration, test = split_chronologically(rows, args.calibration_fraction, args.embargo_calendar_days)
    paths = load_daily_paths(args.daily_dir)
    report = {
        "status": "complete", "research_only": True, "execution_enabled": False,
        "warning": "Retrospective fixed-rule diagnostic only. Stop fills use a conservative gap-at-open rule and a same-day stop-price fill otherwise; no result authorizes execution.",
        "calibration_fraction": args.calibration_fraction, "embargo_calendar_days": args.embargo_calendar_days,
        "round_trip_cost_pct": args.round_trip_cost_pct, "calibration_rows": len(calibration), "test_rows": len(test),
        "input_artifacts": {
            "base_rows_sha256": file_sha256(args.base_rows), "option_features_sha256": file_sha256(args.option_features),
            "technical_model_sha256": file_sha256(args.technical_model),
        },
        "results": [select_with_stop(calibration, test, paths, 0.25, stop, args.max_open_positions, args.round_trip_cost_pct) for stop in args.stop_loss_pct],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
