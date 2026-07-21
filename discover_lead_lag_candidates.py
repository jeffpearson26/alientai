from __future__ import annotations

"""Discover stable, market-residualized cross-symbol lead-lag candidates.

This is hypothesis generation only. It ranks relationships that retain direction
across chronological train/test partitions; it is not a trading signal generator.
"""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping


LAGS = (1, 2, 3, 5, 10)


def read_returns(path: Path) -> dict[str, dict[str, float]]:
    output: dict[str, dict[str, float]] = defaultdict(dict)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            symbol = str(row.get("symbol") or "").strip().upper()
            date = str(row.get("date") or "").strip()
            try:
                value = float(row.get("return_1d_pct"))
            except (TypeError, ValueError):
                continue
            if symbol and len(date) == 10 and math.isfinite(value):
                output[symbol][date] = value
    return dict(output)


def correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3 or len(left) != len(right):
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    left_sum = sum((a - left_mean) ** 2 for a in left)
    right_sum = sum((b - right_mean) ** 2 for b in right)
    if left_sum <= 0 or right_sum <= 0:
        return None
    return numerator / math.sqrt(left_sum * right_sum)


def partial_correlation(left: list[float], right: list[float], control: list[float]) -> float | None:
    """Correlation of left/right after removing a linear target-history control."""
    if len(left) < 3 or len(left) != len(right) or len(left) != len(control):
        return None
    control_mean = sum(control) / len(control)
    control_var = sum((value - control_mean) ** 2 for value in control)
    if control_var <= 0:
        return correlation(left, right)

    def residual(values: list[float]) -> list[float]:
        value_mean = sum(values) / len(values)
        beta = sum((value - value_mean) * (item - control_mean) for value, item in zip(values, control)) / control_var
        return [value - value_mean - beta * (item - control_mean) for value, item in zip(values, control)]

    return correlation(residual(left), residual(right))


def fisher_two_sided_p_value(value: float, samples: int) -> float:
    """Approximate two-sided p-value for correlation using Fisher's transform."""
    if samples <= 3 or not math.isfinite(value):
        return 1.0
    clipped = max(-0.999999, min(0.999999, value))
    z = math.atanh(clipped) * math.sqrt(samples - 3)
    return min(1.0, math.erfc(abs(z) / math.sqrt(2.0)))


def pair_samples(
    source: Mapping[str, float], target: Mapping[str, float], market: Mapping[str, float], lag: int
) -> list[tuple[str, float, float, float]]:
    sessions = sorted(set(source) & set(target) & set(market))
    samples = []
    for index in range(len(sessions) - lag):
        source_date, target_date = sessions[index], sessions[index + lag]
        samples.append((
            source_date,
            source[source_date] - market[source_date],
            target[target_date] - market[target_date],
            target[source_date] - market[source_date],
        ))
    return samples


def stable_candidates(
    returns: Mapping[str, Mapping[str, float]],
    market: Mapping[str, float],
    *,
    lags: Iterable[int] = LAGS,
    min_samples: int = 250,
    minimum_abs_correlation: float = 0.06,
    alpha: float = 0.05,
) -> list[dict[str, Any]]:
    symbols = sorted(returns)
    provisional = []
    tests_evaluated = 0
    for source_symbol in symbols:
        for target_symbol in symbols:
            if source_symbol == target_symbol:
                continue
            for lag in lags:
                samples = pair_samples(returns[source_symbol], returns[target_symbol], market, lag)
                if len(samples) < min_samples:
                    continue
                first = len(samples) // 3
                second = first * 2
                train, validation, test = samples[:first], samples[first:second], samples[second:]
                if min(len(train), len(validation), len(test)) < 3:
                    continue
                train_corr = partial_correlation([x[1] for x in train], [x[2] for x in train], [x[3] for x in train])
                validation_corr = partial_correlation([x[1] for x in validation], [x[2] for x in validation], [x[3] for x in validation])
                test_corr = partial_correlation([x[1] for x in test], [x[2] for x in test], [x[3] for x in test])
                if train_corr is None or validation_corr is None or test_corr is None:
                    continue
                tests_evaluated += 1
                # Select only from train/validation. The final partition is held out
                # and reported, never used to choose a relationship.
                if train_corr * validation_corr <= 0:
                    continue
                stability = min(abs(train_corr), abs(validation_corr))
                if stability < minimum_abs_correlation:
                    continue
                provisional.append({
                    "source_symbol": source_symbol,
                    "target_symbol": target_symbol,
                    "lag_sessions": lag,
                    "samples": len(samples),
                    "train_samples": len(train),
                    "validation_samples": len(validation),
                    "test_samples": len(test),
                    "train_residual_correlation": round(train_corr, 8),
                    "validation_residual_correlation": round(validation_corr, 8),
                    "test_residual_correlation": round(test_corr, 8),
                    "stability_score": round(stability, 8),
                    "direction": "same" if train_corr > 0 else "opposite",
                    "validation_p_value": fisher_two_sided_p_value(validation_corr, len(validation)),
                    "held_out_test_p_value": fisher_two_sided_p_value(test_corr, len(test)),
                })
    output = []
    for row in provisional:
        corrected = min(1.0, row["validation_p_value"] * max(1, tests_evaluated))
        if corrected <= alpha:
            row["bonferroni_validation_p_value"] = corrected
            row["tests_evaluated"] = tests_evaluated
            output.append(row)
    return sorted(output, key=lambda row: (-row["stability_score"], -row["samples"], row["source_symbol"], row["target_symbol"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--returns", type=Path, required=True)
    parser.add_argument("--market-returns", type=Path, required=True)
    parser.add_argument("--market-symbol", default="SPY")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-samples", type=int, default=250)
    parser.add_argument("--minimum-abs-correlation", type=float, default=0.06)
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args()
    returns = read_returns(args.returns)
    market_rows = read_returns(args.market_returns)
    market = market_rows.get(str(args.market_symbol).upper(), {})
    if not market:
        raise SystemExit(f"Missing market symbol {args.market_symbol} in {args.market_returns}")
    candidates = stable_candidates(
        returns, market, min_samples=args.minimum_samples,
        minimum_abs_correlation=args.minimum_abs_correlation, alpha=args.alpha,
    )
    result = {
        "status": "complete",
        "research_only": True,
        "note": "Lead-lag partial correlations control for SPY and the target's current return. Candidate selection uses only the first two chronological windows and a conservative Bonferroni filter; the final window is held out and reported without influencing selection. They remain research hypotheses, not trading signals; sector controls and economic-value evaluation remain required.",
        "symbols_scanned": len(returns),
        "market_symbol": str(args.market_symbol).upper(),
        "lags": list(LAGS),
        "minimum_samples": args.minimum_samples,
        "minimum_abs_correlation": args.minimum_abs_correlation,
        "alpha": args.alpha,
        "candidates": candidates,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "symbols_scanned": len(returns), "candidates": len(candidates), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
