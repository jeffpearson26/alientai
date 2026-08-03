from __future__ import annotations

"""Train isolated 1/5/20-session catalyst-context ablations.

This is a research program only.  It never writes selections, settings, or
orders.  Basket fractions are chosen on validation and opened once on test.
"""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from train_natural_technical_context import (
    chronological_split,
    matrix,
    read_jsonl,
    technical_feature_names,
)


HORIZON_THRESHOLDS = {1: 2.0, 5: 5.0, 20: 10.0}
FRACTIONS = (0.10, 0.20, 0.30, 0.50)
STAGES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("technical", ("technical_", "return_", "realized_volatility_")),
    ("technical_premarket", (
        "technical_", "return_", "realized_volatility_", "model_premarket_",
    )),
    ("technical_premarket_earnings", (
        "technical_", "return_", "realized_volatility_", "model_premarket_",
        "narrative_earnings_", "narrative_fund_",
    )),
    ("technical_premarket_earnings_news", (
        "technical_", "return_", "realized_volatility_", "model_premarket_",
        "narrative_earnings_", "narrative_fund_", "narrative_news_",
    )),
    ("technical_premarket_calls", (
        "technical_", "return_", "realized_volatility_", "model_premarket_", "model_call_",
    )),
    ("technical_premarket_earnings_calls", (
        "technical_", "return_", "realized_volatility_", "model_premarket_",
        "narrative_earnings_", "narrative_fund_", "model_call_",
    )),
    ("technical_premarket_earnings_news_calls", (
        "technical_", "return_", "realized_volatility_", "model_premarket_",
        "narrative_earnings_", "narrative_fund_", "narrative_news_", "model_call_",
    )),
    ("technical_premarket_earnings_calls_analyst", (
        "technical_", "return_", "realized_volatility_", "model_premarket_",
        "narrative_earnings_", "narrative_fund_", "model_call_",
        "model_analyst_proxy_",
    )),
    ("technical_premarket_calls_analyst", (
        "technical_", "return_", "realized_volatility_", "model_premarket_", "model_call_",
        "model_analyst_proxy_",
    )),
    ("technical_premarket_calls_analyst_short_interest", (
        "technical_", "return_", "realized_volatility_", "model_premarket_", "model_call_",
        "model_analyst_proxy_", "short_interest_",
    )),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def trade_metrics(values: Sequence[float], threshold: float) -> dict[str, Any]:
    if not values:
        return {
            "count": 0, "mean_net_return_pct": None, "median_net_return_pct": None,
            "positive_rate": None, "large_move_rate": None, "fifth_percentile_pct": None,
        }
    array = np.asarray(values, dtype=float)
    return {
        "count": int(len(array)),
        "mean_net_return_pct": round(float(np.mean(array)), 6),
        "median_net_return_pct": round(float(np.median(array)), 6),
        "positive_rate": round(float(np.mean(array > 0)), 6),
        "large_move_rate": round(float(np.mean(array >= threshold)), 6),
        "fifth_percentile_pct": round(float(np.percentile(array, 5)), 6),
    }


def select_daily(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    target: str,
    fraction: float,
) -> list[float]:
    by_date: dict[str, list[tuple[float, str, float]]] = defaultdict(list)
    for row, score in zip(rows, scores):
        by_date[str(row["market_date"])].append(
            (float(score), str(row["symbol"]), float(row[target]))
        )
    values: list[float] = []
    for day in sorted(by_date):
        candidates = sorted(by_date[day], key=lambda item: (-item[0], item[1]))
        count = max(1, int(np.ceil(len(candidates) * fraction)))
        values.extend(item[2] for item in candidates[:count])
    return values


def evaluate_fractions(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    target: str,
    threshold: float,
) -> dict[str, dict[str, Any]]:
    return {
        str(fraction): trade_metrics(select_daily(rows, scores, target, fraction), threshold)
        for fraction in FRACTIONS
    }


def choose_fraction(metrics_by_fraction: Mapping[str, Mapping[str, Any]]) -> float:
    eligible = [
        (float(name), values)
        for name, values in metrics_by_fraction.items()
        if int(values["count"]) >= 20
    ]
    if not eligible:
        raise ValueError("validation has fewer than 20 selected observations")
    return max(
        eligible,
        key=lambda item: (
            float(item[1]["mean_net_return_pct"]),
            float(item[1]["positive_rate"]),
            int(item[1]["count"]),
        ),
    )[0]


def train_one(
    rows: Sequence[Mapping[str, Any]],
    horizon: int,
    stage: str,
    prefixes: Sequence[str],
    output_dir: Path,
    train_fraction: float,
    validation_fraction: float,
) -> dict[str, Any]:
    target = f"label_{horizon}d_net_return_pct"
    label_end = f"label_{horizon}d_exit_market_date"
    threshold = HORIZON_THRESHOLDS[horizon]
    usable = [
        row for row in rows
        if row.get(target) is not None and row.get(label_end) and row.get("market_date")
    ]
    names = technical_feature_names(usable, prefixes)
    x = matrix(usable, names)
    y = np.asarray([float(row[target]) >= threshold for row in usable], dtype=np.int32)
    train_idx, validation_idx, test_idx, split = chronological_split(
        usable, train_fraction, validation_fraction, 1, label_end_field=label_end,
    )
    train_data = lgb.Dataset(x[train_idx], label=y[train_idx], feature_name=names)
    validation_data = lgb.Dataset(
        x[validation_idx], label=y[validation_idx], reference=train_data, feature_name=names
    )
    model = lgb.train(
        {
            "objective": "binary", "metric": ["binary_logloss", "auc"],
            "learning_rate": 0.025, "num_leaves": 15, "min_data_in_leaf": 20,
            # Full feature participation is intentional. Subsampling here would
            # confound a nested feature-family ablation because merely adding
            # zero-gain columns changes which baseline columns are sampled.
            "feature_fraction": 1.0, "lambda_l1": 2.0, "lambda_l2": 8.0,
            "verbosity": -1, "seed": 42, "force_col_wise": True,
        },
        train_data,
        num_boost_round=500,
        valid_sets=[validation_data],
        valid_names=["validation"],
        callbacks=[lgb.early_stopping(40, verbose=False), lgb.log_evaluation(0)],
    )
    predict = lambda indexes: model.predict(x[indexes], num_iteration=model.best_iteration)
    validation_rows = [usable[index] for index in validation_idx]
    test_rows = [usable[index] for index in test_idx]
    validation_scores = predict(validation_idx)
    test_scores = predict(test_idx)
    validation_fractions = evaluate_fractions(
        validation_rows, validation_scores, target, threshold
    )
    selected_fraction = choose_fraction(validation_fractions)
    test_fractions = evaluate_fractions(test_rows, test_scores, target, threshold)

    model_dir = output_dir / f"{horizon}d" / stage
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "model.txt"
    model.save_model(str(model_path), num_iteration=model.best_iteration)
    importance = sorted(
        (
            {"feature": name, "gain": round(float(gain), 6)}
            for name, gain in zip(names, model.feature_importance(importance_type="gain"))
        ),
        key=lambda item: item["gain"],
        reverse=True,
    )
    return {
        "horizon_sessions": horizon,
        "stage": stage,
        "target": target,
        "large_move_threshold_pct": threshold,
        "rows": len(usable),
        "features": len(names),
        "feature_names": names,
        "best_iteration": int(model.best_iteration),
        "split": split,
        "class_rates": {
            "train": round(float(np.mean(y[train_idx])), 6),
            "validation": round(float(np.mean(y[validation_idx])), 6),
            "test": round(float(np.mean(y[test_idx])), 6),
        },
        "validation_fractions": validation_fractions,
        "validation_selected_fraction": selected_fraction,
        "test_at_validation_selected_fraction": test_fractions[str(selected_fraction)],
        "test_all_fractions_diagnostic": test_fractions,
        "test_all_universe_control": trade_metrics(
            [float(row[target]) for row in test_rows], threshold
        ),
        "top_features": importance[:20],
        "model_path": str(model_path),
        "model_sha256": sha256(model_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--train-fraction", type=float, default=0.60)
    parser.add_argument("--validation-fraction", type=float, default=0.20)
    args = parser.parse_args()

    rows = read_jsonl(args.input)
    results = []
    for horizon in HORIZON_THRESHOLDS:
        for stage, prefixes in STAGES:
            results.append(train_one(
                rows, horizon, stage, prefixes, args.output_dir,
                args.train_fraction, args.validation_fraction,
            ))
            print(
                f"trained horizon={horizon} stage={stage} "
                f"test_mean={results[-1]['test_at_validation_selected_fraction']['mean_net_return_pct']}"
            )
    report = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "design": "FUTURE_AI_SEMICONDUCTOR_MULTI_HORIZON_MODEL.md",
        "input": str(args.input),
        "input_sha256": sha256(args.input),
        "universe_symbols": sorted({str(row["symbol"]) for row in rows}),
        "available_feature_families": [
            "technical and market context", "premarket through 09:25 ET",
            "historical unusual call activity", "conservative analyst-headline proxy",
            "FINRA short interest",
        ],
        "deferred_incomplete_feature_families": [
            "historical point-in-time fundamentals and guidance",
            "structured licensed analyst rating history",
            "complete general news sentiment and novelty",
            "scheduled catalyst calendar",
            "vintage industry demand and hyperscaler capex series",
            "historical point-in-time valuation",
        ],
        "warning":
            "The test period is now observed. Results cannot be used to retune these variants.",
        "models": results,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "multi_horizon_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report_path), "models": len(results)}, indent=2))


if __name__ == "__main__":
    main()
