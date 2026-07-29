from __future__ import annotations

"""Time-ordered, capacity-limited diagnostic for contextual unusual-call ideas.

This evaluator is deliberately research-only.  It selects a technical cutoff
from an earlier calibration period, leaves a calendar embargo, and evaluates
only later rows.  It does not make an already-explored data period prospective.
"""

import argparse
import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.research.rare_signal_gate import evaluate_rare_signal_gate
from evaluate_matched_winner_full_universe import selection_metrics
from evaluate_unusual_call_contexts import score_rows
from evaluate_unusual_call_outcomes import join_option_outcomes, read_jsonl


def file_sha256(path: Path) -> str:
    """Return a stable artifact identity so a report can be reproduced later."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def daily_archive_sha256(directory: Path) -> str:
    """Fingerprint every daily CSV name and byte content in deterministic order."""
    paths = sorted(directory.glob("*_schwab_1d_max.csv"), key=lambda item: item.name)
    if not paths:
        raise ValueError("daily directory contains no Schwab CSV files")
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(file_sha256(path)))
    return digest.hexdigest()


def split_chronologically(rows: Sequence[Mapping[str, Any]], calibration_fraction: float, embargo_calendar_days: int) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if not 0 < calibration_fraction < 1:
        raise ValueError("calibration_fraction must be in (0, 1)")
    days = sorted({date.fromisoformat(str(row["market_date"])) for row in rows})
    if len(days) < 3:
        raise ValueError("at least three distinct market dates are required")
    cutoff = days[max(0, min(len(days) - 2, int(len(days) * calibration_fraction) - 1))]
    test_start = cutoff + timedelta(days=embargo_calendar_days + 1)
    calibration = [row for row in rows if date.fromisoformat(str(row["market_date"])) <= cutoff]
    test = [row for row in rows if date.fromisoformat(str(row["market_date"])) >= test_start]
    if not calibration or not test:
        raise ValueError("chronological split produced an empty calibration or test slice")
    return calibration, test


def capacity_limited(rows: Sequence[Mapping[str, Any]], max_open_positions: int) -> list[Mapping[str, Any]]:
    if max_open_positions < 1:
        raise ValueError("max_open_positions must be positive")
    active_exits: list[date] = []
    selected = []
    for row in sorted(rows, key=lambda item: (str(item.get("entry_market_date") or item["market_date"]), -float(item["technical_context_score"]))):
        day = date.fromisoformat(str(row.get("entry_market_date") or row["market_date"]))
        # Free capital only after the exit-session close, a conservative rule.
        active_exits = [exit_day for exit_day in active_exits if day <= exit_day]
        if len(active_exits) >= max_open_positions:
            continue
        future = str(row.get("future_market_date") or "")
        try:
            exit_day = date.fromisoformat(future)
        except ValueError:
            continue
        if exit_day <= day:
            continue
        selected.append(row)
        active_exits.append(exit_day)
    return selected


def load_daily_closes(directory: Path) -> dict[str, dict[date, float]]:
    output: dict[str, dict[date, float]] = {}
    for path in sorted(directory.glob("*_schwab_1d_max.csv")):
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            continue
        symbol = str(rows[0].get("symbol") or "").strip().upper()
        closes: dict[date, float] = {}
        for row in rows:
            try:
                day = date.fromisoformat(str(row.get("date") or ""))
                close = float(row.get("close"))
            except (TypeError, ValueError):
                continue
            if np.isfinite(close) and close > 0:
                closes[day] = close
        if symbol and closes:
            output[symbol] = closes
    if not output:
        raise ValueError("daily directory contains no usable close histories")
    return output


def load_daily_bars(directory: Path) -> dict[str, dict[date, dict[str, float]]]:
    """Load positive open/close prices for executable entry/exit reconciliation."""
    output: dict[str, dict[date, dict[str, float]]] = {}
    for path in sorted(directory.glob("*_schwab_1d_max.csv")):
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            continue
        symbol = str(rows[0].get("symbol") or "").strip().upper()
        bars: dict[date, dict[str, float]] = {}
        for row in rows:
            try:
                day = date.fromisoformat(str(row.get("date") or ""))
                open_price = float(row.get("open"))
                close_price = float(row.get("close"))
            except (TypeError, ValueError):
                continue
            if np.isfinite(open_price) and open_price > 0 and np.isfinite(close_price) and close_price > 0:
                bars[day] = {"open": open_price, "close": close_price}
        if symbol and bars:
            output[symbol] = bars
    if not output:
        raise ValueError("daily directory contains no usable open/close histories")
    return output


def capital_scaled_drawdown(
    rows: Sequence[Mapping[str, Any]],
    daily_closes: Mapping[str, Mapping[date, Any]],
    max_open_positions: int,
    round_trip_cost_pct: float,
    label_return_key: str = "label_forward_return_5d_pct",
) -> dict[str, Any]:
    """Mark a fixed-slot portfolio to market daily, leaving unused slots in cash."""
    if max_open_positions < 1:
        raise ValueError("max_open_positions must be positive")
    trades = []
    maximum_label_alignment_error = 0.0

    def bar_value(value: Any, field: str) -> float:
        if isinstance(value, Mapping):
            return float(value[field])
        if field != "close":
            raise ValueError("open price unavailable in close-only daily path")
        return float(value)

    def resolve_day(
        path: Mapping[date, Any], nominal_day: date, expected_price: float, field: str,
    ) -> date:
        candidates = [
            day for day, bar in path.items()
            if abs((day - nominal_day).days) <= 3
            and abs(bar_value(bar, field) / expected_price - 1.0) <= 0.00001
        ]
        if not candidates:
            raise ValueError(f"no price-anchored candle near {nominal_day} at {expected_price}")
        return min(candidates, key=lambda day: (abs((day - nominal_day).days), day))

    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        try:
            nominal_entry_day = date.fromisoformat(str(row.get("entry_market_date") or row["market_date"]))
            nominal_exit_day = date.fromisoformat(str(row["future_market_date"]))
            path = daily_closes[symbol]
            entry_price = float(row.get("entry_price") or row.get("close") or bar_value(path[nominal_entry_day], "close"))
            entry_field = "open" if row.get("entry_market_date") else "close"
            entry_day = resolve_day(path, nominal_entry_day, entry_price, entry_field)
            if row.get(label_return_key) is not None:
                label_return = float(row[label_return_key])
                expected_exit_price = entry_price * (1.0 + label_return / 100.0)
                exit_day = resolve_day(path, nominal_exit_day, expected_exit_price, "close")
            else:
                exit_day = nominal_exit_day
            exit_price = bar_value(path[exit_day], "close")
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"missing complete daily path for {symbol or '<blank>'}") from exc
        observed_days = sorted(day for day in path if entry_day <= day <= exit_day)
        if not observed_days or observed_days[0] != entry_day or observed_days[-1] != exit_day:
            raise ValueError(f"incomplete entry/exit path for {symbol}")
        if row.get(label_return_key) is not None:
            path_return = (exit_price / entry_price - 1.0) * 100.0
            label_return = float(row[label_return_key])
            alignment_error = abs(path_return - label_return)
            maximum_label_alignment_error = max(maximum_label_alignment_error, alignment_error)
            if alignment_error > 0.001:
                raise ValueError(
                    f"daily path does not reproduce label for {symbol}: "
                    f"{path_return:.6f} versus {label_return:.6f}"
                )
        trades.append({
            "symbol": symbol, "entry_day": entry_day, "exit_day": exit_day,
            "entry_price": entry_price, "exit_price": exit_price, "path": path,
        })
    if not trades:
        return {
            "capital_scaled_max_drawdown_pct": 0.0,
            "capital_scaled_final_return_pct": 0.0,
            "capital_scaled_observed_days": 0,
            "capital_scaled_peak_open_positions": 0,
            "maximum_label_alignment_error_pct": 0.0,
        }
    all_days = sorted({day for trade in trades for day in trade["path"] if trade["entry_day"] <= day <= trade["exit_day"]})
    entries: dict[date, list[dict[str, Any]]] = {}
    for trade in trades:
        entries.setdefault(trade["entry_day"], []).append(trade)
    cash, equity, peak, worst = 1.0, 1.0, 1.0, 0.0
    active: list[dict[str, Any]] = []
    peak_open = 0
    for day in all_days:
        # Existing positions are marked at the latest available close no later
        # than this portfolio day. New entries may use the open, but are marked
        # to that session's close before the daily equity snapshot.
        for position in active:
            if day in position["path"]:
                position["last_price"] = bar_value(position["path"][day], "close")
        exiting = [position for position in active if position["exit_day"] == day]
        for position in exiting:
            proceeds = position["shares"] * position["last_price"]
            proceeds *= 1.0 - round_trip_cost_pct / 100.0
            cash += proceeds
            active.remove(position)
        marked_equity = cash + sum(position["shares"] * position["last_price"] for position in active)
        for trade in entries.get(day, []):
            if len(active) >= max_open_positions:
                raise ValueError("selected rows violate fixed-slot capacity")
            # Never borrow to refill a slot after other open positions have
            # appreciated. Invest at most one target slot and at most cash.
            slot_notional = min(cash, marked_equity / max_open_positions)
            if slot_notional <= 0:
                raise ValueError("selected entry has no available cash")
            cash -= slot_notional
            entry_close = bar_value(trade["path"][day], "close")
            active.append({
                **trade,
                "shares": slot_notional / trade["entry_price"],
                "last_price": entry_close,
            })
        peak_open = max(peak_open, len(active))
        equity = cash + sum(position["shares"] * position["last_price"] for position in active)
        peak = max(peak, equity)
        worst = min(worst, (equity / peak - 1.0) * 100.0)
    return {
        "capital_scaled_max_drawdown_pct": round(worst, 6),
        "capital_scaled_final_return_pct": round((equity - 1.0) * 100.0, 6),
        "capital_scaled_observed_days": len(all_days),
        "capital_scaled_peak_open_positions": peak_open,
        "maximum_label_alignment_error_pct": round(maximum_label_alignment_error, 9),
    }


def evaluate_cutoffs(calibration_rows: Sequence[Mapping[str, Any]], test_rows: Sequence[Mapping[str, Any]], fractions: Sequence[float], max_open_positions: int, round_trip_cost_pct: float, daily_closes: Mapping[str, Mapping[date, float]] | None = None) -> list[dict[str, Any]]:
    calibration_scores = np.asarray([float(row["technical_context_score"]) for row in calibration_rows], dtype=float)
    output = []
    for fraction in fractions:
        if not 0 < fraction <= 1:
            raise ValueError("fractions must be in (0, 1]")
        cutoff = float(np.quantile(calibration_scores, 1.0 - fraction))
        candidates = [row for row in test_rows if row.get("call_volume_unusual") and float(row["technical_context_score"]) >= cutoff]
        selected = capacity_limited(candidates, max_open_positions)
        metrics = selection_metrics(selected, round_trip_cost_pct)
        capital_metrics = capital_scaled_drawdown(
            selected, daily_closes, max_open_positions, round_trip_cost_pct,
        ) if daily_closes is not None else {}
        capital_gate = None
        if capital_metrics:
            corrected_gate_metrics = {
                **metrics,
                "approximate_cohort_max_drawdown_pct": capital_metrics["capital_scaled_max_drawdown_pct"],
            }
            capital_gate = evaluate_rare_signal_gate(corrected_gate_metrics)
        output.append({
            "technical_top_fraction_selected_on_calibration": fraction,
            "technical_score_cutoff_from_calibration": cutoff,
            "test_unusual_call_candidates": len(candidates),
            "max_open_positions": max_open_positions,
            **metrics,
            **capital_metrics,
            "rare_signal_gate": evaluate_rare_signal_gate(metrics),
            "capital_scaled_rare_signal_gate": capital_gate,
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Chronological contextual unusual-call portfolio diagnostic.")
    parser.add_argument("--base-rows", type=Path, required=True)
    parser.add_argument("--option-features", type=Path, required=True)
    parser.add_argument("--technical-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--calibration-fraction", type=float, default=0.60)
    parser.add_argument("--embargo-calendar-days", type=int, default=7)
    parser.add_argument("--max-open-positions", type=int, default=5)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    parser.add_argument("--daily-dir", type=Path)
    args = parser.parse_args()
    raw_rows = join_option_outcomes(read_jsonl(args.base_rows), read_jsonl(args.option_features))
    model = lgb.Booster(model_file=str(args.technical_model))
    rows = score_rows(raw_rows, model)
    calibration, test = split_chronologically(rows, args.calibration_fraction, args.embargo_calendar_days)
    report = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "warning": "Retrospective chronological diagnostic only. Because this panel was previously explored, an independent future or untouched archive is still required for confirmation.",
        "calibration_rows": len(calibration),
        "test_rows": len(test),
        "calibration_fraction": args.calibration_fraction,
        "embargo_calendar_days": args.embargo_calendar_days,
        "round_trip_cost_pct": args.round_trip_cost_pct,
        "input_artifacts": {
            "base_rows_path": str(args.base_rows),
            "base_rows_sha256": file_sha256(args.base_rows),
            "option_features_path": str(args.option_features),
            "option_features_sha256": file_sha256(args.option_features),
            "technical_model_path": str(args.technical_model),
            "technical_model_sha256": file_sha256(args.technical_model),
            "daily_archive_path": str(args.daily_dir) if args.daily_dir else None,
            "daily_archive_sha256": daily_archive_sha256(args.daily_dir) if args.daily_dir else None,
        },
        "results": evaluate_cutoffs(
            calibration, test, (0.25, 0.10, 0.05), args.max_open_positions,
            args.round_trip_cost_pct,
            load_daily_closes(args.daily_dir) if args.daily_dir else None,
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
