from __future__ import annotations

"""Validation-locked trailing-correlation control for Nasdaq candidates."""

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from evaluate_context_portfolio import (
    capital_scaled_drawdown,
    daily_archive_sha256,
    file_sha256,
    load_daily_closes,
)
from evaluate_nasdaq100_clone_portfolio import read_jsonl, score_rows, trade_metrics


def trailing_returns(
    closes: Mapping[date, float], as_of: date, sessions: int,
) -> dict[date, float]:
    days = sorted(day for day in closes if day <= as_of)
    days = days[-(sessions + 1):]
    return {
        current: float(closes[current] / closes[previous] - 1.0)
        for previous, current in zip(days, days[1:])
        if closes[previous] > 0
    }


def trailing_correlation(
    first: Mapping[date, float],
    second: Mapping[date, float],
    as_of: date,
    sessions: int = 60,
    minimum_common: int = 40,
) -> float | None:
    left, right = trailing_returns(first, as_of, sessions), trailing_returns(
        second, as_of, sessions
    )
    common = sorted(set(left) & set(right))
    if len(common) < minimum_common:
        return None
    correlation = float(np.corrcoef(
        [left[day] for day in common], [right[day] for day in common]
    )[0, 1])
    return correlation if np.isfinite(correlation) else None


def correlation_limited(
    rows: Sequence[Mapping[str, Any]],
    daily_closes: Mapping[str, Mapping[date, float]],
    max_open_positions: int,
    maximum_correlation: float,
    sessions: int = 60,
    minimum_common: int = 40,
) -> tuple[list[Mapping[str, Any]], dict[str, int]]:
    if max_open_positions < 1:
        raise ValueError("max_open_positions must be positive")
    active: list[tuple[date, str]] = []
    selected = []
    rejected_correlation = rejected_missing = 0
    for row in sorted(
        rows,
        key=lambda item: (
            str(item["market_date"]),
            -float(item["technical_context_score"]),
            str(item["symbol"]),
        ),
    ):
        day = date.fromisoformat(str(row["market_date"]))
        active = [(exit_day, symbol) for exit_day, symbol in active if day <= exit_day]
        if len(active) >= max_open_positions:
            continue
        symbol = str(row.get("symbol") or "").upper()
        try:
            exit_day = date.fromisoformat(str(row["future_market_date"]))
            path = daily_closes[symbol]
        except (KeyError, ValueError):
            rejected_missing += 1
            continue
        if exit_day <= day or any(open_symbol == symbol for _, open_symbol in active):
            continue
        blocked = False
        for _, open_symbol in active:
            correlation = trailing_correlation(
                path,
                daily_closes.get(open_symbol, {}),
                day,
                sessions,
                minimum_common,
            )
            if correlation is None:
                rejected_missing += 1
                blocked = True
                break
            if correlation > maximum_correlation:
                rejected_correlation += 1
                blocked = True
                break
        if blocked:
            continue
        selected.append(row)
        active.append((exit_day, symbol))
    return selected, {
        "rejected_for_correlation": rejected_correlation,
        "rejected_for_missing_correlation_history": rejected_missing,
    }


def choose_threshold(
    diagnostics: Sequence[Mapping[str, Any]], minimum_signals: int,
) -> Mapping[str, Any]:
    eligible = [
        row for row in diagnostics
        if int(row["signals"]) >= minimum_signals
        and float(row["mean_net_return_pct"]) > 0.0
        and float(row["median_net_return_pct"]) > 0.0
        and float(row["net_win_rate_pct"]) >= 50.0
        and float(row["capital_scaled_max_drawdown_pct"]) >= -20.0
    ]
    if not eligible:
        raise ValueError("no correlation threshold passes validation gates")
    return max(
        eligible,
        key=lambda row: (
            float(row["capital_scaled_final_return_pct"])
            / max(abs(float(row["capital_scaled_max_drawdown_pct"])), 0.01),
            float(row["capital_scaled_final_return_pct"]),
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--training-report", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--score-cutoff", type=float, required=True)
    parser.add_argument(
        "--correlation-thresholds", type=float, nargs="+",
        default=[0.60, 0.75, 0.90, 1.01],
    )
    parser.add_argument("--minimum-validation-signals", type=int, default=20)
    parser.add_argument("--max-open-positions", type=int, default=5)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()

    training = json.loads(args.training_report.read_text(encoding="utf-8"))
    rows = read_jsonl(args.rows)
    model = lgb.Booster(model_file=str(args.model))
    scored = score_rows(rows, model, training["feature_names"])
    validation_start = date.fromisoformat(training["split"]["validation_start"])
    validation_end = date.fromisoformat(training["split"]["validation_end"])
    test_start = date.fromisoformat(training["split"]["test_start"])
    validation = [
        row for row in scored
        if validation_start <= date.fromisoformat(row["market_date"]) <= validation_end
        and float(row["technical_context_score"]) >= args.score_cutoff
    ]
    test = [
        row for row in scored
        if date.fromisoformat(row["market_date"]) >= test_start
        and float(row["technical_context_score"]) >= args.score_cutoff
    ]
    closes = load_daily_closes(args.daily_dir)
    diagnostics = []
    for threshold in args.correlation_thresholds:
        selected, rejected = correlation_limited(
            validation, closes, args.max_open_positions, threshold
        )
        diagnostics.append({
            "maximum_correlation": threshold,
            **trade_metrics(selected, args.round_trip_cost_pct),
            **capital_scaled_drawdown(
                selected, closes, args.max_open_positions, args.round_trip_cost_pct
            ),
            **rejected,
        })
    common_report = {
        "research_only": True,
        "execution_enabled": False,
        "warning": "The confirmation period has been used by earlier Nasdaq studies and is not a fresh untouched test.",
        "selection_contract": "correlation threshold selected on validation by capital-return-to-drawdown ratio after fixed gates",
        "artifacts": {
            "rows_sha256": file_sha256(args.rows),
            "model_sha256": file_sha256(args.model),
            "training_report_sha256": file_sha256(args.training_report),
            "daily_archive_sha256": daily_archive_sha256(args.daily_dir),
        },
        "settings": {
            "locked_score_cutoff": args.score_cutoff,
            "candidate_correlation_thresholds": args.correlation_thresholds,
            "trailing_sessions": 60,
            "minimum_common_returns": 40,
            "max_open_positions": args.max_open_positions,
            "round_trip_cost_pct": args.round_trip_cost_pct,
        },
        "validation_diagnostics": diagnostics,
    }
    try:
        winner = choose_threshold(diagnostics, args.minimum_validation_signals)
    except ValueError as exc:
        report = {
            "status": "research_hold",
            **common_report,
            "reason": str(exc),
            "selected": None,
            "historical_confirmation": None,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return
    selected, rejected = correlation_limited(
        test, closes, args.max_open_positions, float(winner["maximum_correlation"])
    )
    report = {
        "status": "complete",
        **common_report,
        "selected": dict(winner),
        "historical_confirmation_candidates_before_control": len(test),
        "historical_confirmation": {
            **trade_metrics(selected, args.round_trip_cost_pct),
            **capital_scaled_drawdown(
                selected, closes, args.max_open_positions, args.round_trip_cost_pct
            ),
            **rejected,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
