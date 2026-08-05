from __future__ import annotations

"""Score one current Nasdaq-101 panel with a validation-approved frozen model."""

import argparse
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np

from alientai_v2.research.long_horizon_technicals import (
    long_horizon_technical_features,
)
from build_nasdaq101_126session_technical_panel import (
    BENCHMARKS,
    MIN_HISTORY,
    RELATIVE_WINDOWS,
    TECHNICAL_WINDOW,
    benchmark_context,
    beta_and_correlation,
    lag_return,
    read_candidates,
    sha256,
)
from build_nasdaq_qqq_spy_60session_panel import load_adjusted_daily
from train_nasdaq101_126session_technical_model import (
    add_cross_sectional_feature_ranks,
    cross_sectional_score_percentiles,
    matrix,
    select_daily_with_diagnostics,
)


def latest_rows(
    daily: dict[str, list[dict[str, Any]]],
    candidates: list[str],
) -> tuple[str, list[dict[str, Any]]]:
    latest_dates = {
        symbol: str(daily[symbol][-1]["market_date"])
        for symbol in [*candidates, *BENCHMARKS]
    }
    if len(set(latest_dates.values())) != 1:
        raise ValueError(f"latest dates are not identical: {latest_dates}")
    decision_date = next(iter(latest_dates.values()))
    benchmark_features = {}
    for benchmark in BENCHMARKS:
        index = len(daily[benchmark]) - 1
        benchmark_features.update(
            benchmark_context(
                benchmark.lower(), daily[benchmark], index
            )
        )
    rows = []
    for symbol in candidates:
        candles = daily[symbol]
        index = len(candles) - 1
        if index < MIN_HISTORY - 1:
            raise ValueError(f"insufficient history: {symbol}")
        features = long_horizon_technical_features(
            candles[max(0, index + 1 - TECHNICAL_WINDOW) : index + 1]
        )
        relative = {}
        for benchmark in BENCHMARKS:
            benchmark_rows = daily[benchmark]
            benchmark_index = len(benchmark_rows) - 1
            for window in RELATIVE_WINDOWS:
                stock_return = lag_return(candles, index, window)
                benchmark_return = lag_return(
                    benchmark_rows, benchmark_index, window
                )
                relative[
                    f"relative_to_{benchmark.lower()}_{window}d_pct"
                ] = (
                    stock_return - benchmark_return
                    if stock_return is not None
                    and benchmark_return is not None
                    else None
                )
                beta, correlation = beta_and_correlation(
                    candles,
                    index,
                    benchmark_rows,
                    benchmark_index,
                    window,
                )
                relative[f"beta_to_{benchmark.lower()}_{window}d"] = beta
                relative[
                    f"correlation_to_{benchmark.lower()}_{window}d"
                ] = correlation
        rows.append(
            {
                "symbol": symbol,
                "market_date": decision_date,
                "decision_adjusted_close": float(candles[-1]["close"]),
                **features,
                **benchmark_features,
                **relative,
            }
        )
    return decision_date, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--daily-root", type=Path, required=True)
    parser.add_argument("--candidates-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report_path = args.model_dir / "training_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    threshold = report.get("policy_gate", {}).get("chosen_score_threshold")
    if (
        report.get("status") != "FROZEN_PENDING_PROSPECTIVE"
        or threshold is None
    ):
        raise ValueError("model did not pass validation and cannot be scored")
    classifier_path = Path(report["classifier_model_path"])
    regressor_path = Path(report["return_model_path"])
    calibration_path = Path(report["calibration_path"])
    for path, expected in (
        (classifier_path, report["classifier_model_sha256"]),
        (regressor_path, report["return_model_sha256"]),
        (calibration_path, report["calibration_sha256"]),
    ):
        if sha256(path) != expected:
            raise ValueError(f"frozen artifact hash mismatch: {path}")

    candidates = read_candidates(args.candidates_file)
    daily = {
        symbol: load_adjusted_daily(args.daily_root / f"{symbol}_daily.json")
        for symbol in [*candidates, *BENCHMARKS]
    }
    decision_date, rows = latest_rows(daily, candidates)
    eligibility = report.get("selection_eligibility", {})
    minimum_price = float(
        eligibility.get("minimum_decision_adjusted_price", 0.0)
    )
    minimum_dollar_volume = float(
        eligibility.get("minimum_average_dollar_volume_20d", 0.0)
    )
    rows = [
        row
        for row in rows
        if float(row["decision_adjusted_close"]) >= minimum_price
        and float(row.get("lh_average_dollar_volume_20d") or 0.0)
        >= minimum_dollar_volume
    ]
    add_cross_sectional_feature_ranks(rows)
    names = list(report["features"])
    values = matrix(rows, names)
    classifier = lgb.Booster(model_file=str(classifier_path))
    regressor = lgb.Booster(model_file=str(regressor_path))
    classifier_scores = classifier.predict(
        values, num_iteration=int(report["classifier_best_iteration"])
    )
    return_scores = regressor.predict(
        values, num_iteration=int(report["return_model_best_iteration"])
    )
    standardization = report["ensemble_standardization"]
    scores = 0.5 * (
        (
            classifier_scores - float(standardization["classifier_mean"])
        )
        / float(standardization["classifier_std"])
        + (return_scores - float(standardization["return_mean"]))
        / float(standardization["return_std"])
    )
    score_percentiles = cross_sectional_score_percentiles(
        rows, np.asarray(scores)
    )
    selected, diagnostics = select_daily_with_diagnostics(
        rows, score_percentiles, float(threshold)
    )
    ranked = sorted(
        [
            {
                "symbol": str(row["symbol"]),
                "model_score": round(float(row["model_score"]), 8),
                "model_score_semantics": "cross-sectional percentile",
                "expected_excess_return_over_qqq_model_pct": round(
                    float(return_scores[
                        candidates.index(str(row["symbol"]))
                    ]),
                    6,
                ),
                "positive_excess_return_raw_probability_pct": round(
                    float(
                        classifier_scores[
                            candidates.index(str(row["symbol"]))
                        ]
                    )
                    * 100.0,
                    4,
                ),
            }
            for row in selected
        ],
        key=lambda row: (-row["model_score"], row["symbol"]),
    )
    output = {
        "status": "RESEARCH_SELECTIONS" if ranked else "ABSTENTION",
        "research_only": True,
        "execution_enabled": False,
        "decision_date": decision_date,
        "candidate_universe_count": len(candidates),
        "context_only_symbols": list(BENCHMARKS),
        "horizon_sessions": int(report.get("horizon_sessions", 126)),
        "threshold": float(threshold),
        "selection_diagnostics": diagnostics,
        "selections": ranked,
        "model_report": str(report_path),
        "model_report_sha256": sha256(report_path),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
