from __future__ import annotations

"""Discover cross-stock lead/lag relations on training dates and test them later.

This is a multiple-testing-prone research diagnostic.  It intentionally keeps
discovery and evaluation dates separate and cannot emit trading candidates.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np


def load_returns(daily_dir: Path, symbols: list[str]) -> tuple[list[str], np.ndarray, list[str]]:
    series: dict[str, dict[str, float]] = {}
    excluded = []
    all_dates: set[str] = set()
    for symbol in symbols:
        path = daily_dir / f"{symbol}_schwab_1d_max.csv"
        if not path.exists():
            excluded.append(symbol); continue
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        values: dict[str, float] = {}
        for previous, current in zip(rows, rows[1:]):
            try:
                before, after = float(previous["close"]), float(current["close"])
                if before > 0 and after > 0:
                    values[str(current["date"])] = (after / before - 1.0) * 100.0
            except (KeyError, TypeError, ValueError):
                continue
        if values:
            series[symbol] = values; all_dates.update(values)
        else:
            excluded.append(symbol)
    dates = sorted(all_dates)
    matrix = np.full((len(dates), len(series)), np.nan, dtype=np.float64)
    for column, values in enumerate(series.values()):
        for row, day in enumerate(dates):
            if day in values: matrix[row, column] = values[day]
    return list(series), matrix, dates


def lagged_correlations(values: np.ndarray, lag: int, minimum_observations: int) -> np.ndarray:
    """Pairwise Pearson correlations with only overlapping finite observations."""
    x, y = values[:-lag], values[lag:]
    mx, my = np.isfinite(x).astype(np.float64), np.isfinite(y).astype(np.float64)
    xf, yf = np.nan_to_num(x), np.nan_to_num(y)
    count = mx.T @ my
    sx, sy = xf.T @ my, mx.T @ yf
    sxx, syy, sxy = (xf * xf).T @ my, mx.T @ (yf * yf), xf.T @ yf
    with np.errstate(divide="ignore", invalid="ignore"):
        covariance = sxy - sx * sy / count
        variance_x = sxx - sx * sx / count
        variance_y = syy - sy * sy / count
        correlation = covariance / np.sqrt(variance_x * variance_y)
    correlation[(count < minimum_observations) | ~np.isfinite(correlation)] = np.nan
    return correlation


def discover(values: np.ndarray, symbols: list[str], lags: list[int], minimum_observations: int, maximum_pairs: int) -> list[dict[str, Any]]:
    pairs = []
    for lag in lags:
        corr = lagged_correlations(values, lag, minimum_observations)
        np.fill_diagonal(corr, np.nan)
        for leader, follower in zip(*np.where(np.isfinite(corr))):
            pairs.append({"leader": symbols[leader], "follower": symbols[follower], "lag_days": lag,
                          "train_correlation": float(corr[leader, follower])})
    return sorted(pairs, key=lambda item: -abs(item["train_correlation"]))[:maximum_pairs]


def evaluate_holdout(values: np.ndarray, dates: list[str], symbols: list[str], pairs: list[dict[str, Any]], test_start: str, cost_pct: float) -> dict[str, Any]:
    positions = {symbol: index for index, symbol in enumerate(symbols)}
    signals = []
    for pair in pairs:
        leader, follower, lag, corr = positions[pair["leader"]], positions[pair["follower"]], pair["lag_days"], pair["train_correlation"]
        for index in range(lag, len(dates)):
            if dates[index] < test_start: continue
            lead, target = values[index - lag, leader], values[index, follower]
            if not np.isfinite(lead) or not np.isfinite(target): continue
            predicted_up = corr * lead > 0
            if predicted_up: signals.append(float(target) - cost_pct)
    return {"signals": len(signals), "mean_net_return_pct": float(np.mean(signals)) if signals else None,
            "median_net_return_pct": float(np.median(signals)) if signals else None,
            "win_rate_after_cost": float(np.mean(np.asarray(signals) > 0)) if signals else None}


def main() -> None:
    parser = argparse.ArgumentParser(description="Research-only cross-stock lead/lag holdout study.")
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--train-end", required=True)
    parser.add_argument("--test-start", required=True)
    parser.add_argument("--lags", default="1,2,3,4,5")
    parser.add_argument("--minimum-observations", type=int, default=250)
    parser.add_argument("--maximum-pairs", type=int, default=20)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    symbols = [line.strip().upper() for line in args.symbols_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    names, values, dates = load_returns(args.daily_dir, symbols)
    train = values[np.asarray([day <= args.train_end for day in dates])]
    pairs = discover(train, names, [int(item) for item in args.lags.split(",")], args.minimum_observations, args.maximum_pairs)
    metrics = evaluate_holdout(values, dates, names, pairs, args.test_start, args.round_trip_cost_pct)
    report = {"status": "complete", "research_only": True, "execution_enabled": False,
              "warning": "Cross-stock lead/lag discovery is vulnerable to multiple testing; this holdout is exploratory only.",
              "symbols_loaded": len(names), "excluded_symbols": len(symbols) - len(names), "train_end": args.train_end,
              "test_start": args.test_start, "discovered_pair_count": len(pairs), "holdout_metrics": metrics}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
