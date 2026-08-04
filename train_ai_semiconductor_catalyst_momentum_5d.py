from __future__ import annotations

"""Train the isolated five-session catalyst + momentum research model.

This program has no order path. Fractions are selected using validation only,
then opened once on the chronological test partition.
"""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.research.catalyst_momentum_5d import engineer_rows
from evaluate_context_portfolio import capacity_limited
from train_natural_technical_context import (
    chronological_split,
    matrix,
    read_jsonl,
    technical_feature_names,
)


TARGET = "label_5d_net_return_pct"
LABEL_END = "label_5d_exit_market_date"
TARGET_RETURN_PCT = 2.0
FRACTIONS = (0.10, 0.20, 0.30, 0.50)
MAX_DAILY_SELECTIONS = 5
MAX_OPEN_POSITIONS = 5
STAGES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "technical_setup",
        (
            "technical_", "return_", "realized_volatility_",
            "cm_technical_", "cm_risk_",
        ),
        "cm_technical_eligible",
    ),
    (
        "catalyst_technical",
        (
            "technical_", "return_", "realized_volatility_",
            "narrative_news_", "narrative_earnings_", "model_analyst_proxy_",
            "cm_technical_", "cm_catalyst_", "cm_risk_",
        ),
        "cm_primary_eligible",
    ),
    (
        "catalyst_technical_positioning",
        (
            "technical_", "return_", "realized_volatility_",
            "narrative_news_", "narrative_earnings_", "model_analyst_proxy_",
            "model_call_", "model_option_",
            "cm_technical_", "cm_catalyst_", "cm_positioning_", "cm_risk_",
        ),
        "cm_primary_eligible",
    ),
    (
        "full_catalyst_momentum",
        (
            "technical_", "return_", "realized_volatility_",
            "narrative_news_", "narrative_earnings_", "narrative_fund_",
            "model_analyst_proxy_", "model_call_", "model_option_",
            "insider_", "short_interest_",
            "cm_technical_", "cm_catalyst_", "cm_positioning_",
            "cm_fundamental_", "cm_risk_",
        ),
        "cm_primary_eligible",
    ),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _return_metrics(values: Sequence[float]) -> dict[str, Any]:
    values = np.asarray(values, dtype=float)
    if not len(values):
        return {
            "count": 0, "mean_net_return_pct": None, "median_net_return_pct": None,
            "win_rate": None, "target_2pct_rate": None, "large_5pct_rate": None,
            "fifth_percentile_pct": None, "worst_trade_pct": None,
        }
    return {
        "count": int(len(values)),
        "mean_net_return_pct": round(float(np.mean(values)), 6),
        "median_net_return_pct": round(float(np.median(values)), 6),
        "win_rate": round(float(np.mean(values > 0.0)), 6),
        "target_2pct_rate": round(float(np.mean(values >= 2.0)), 6),
        "large_5pct_rate": round(float(np.mean(values >= 5.0)), 6),
        "fifth_percentile_pct": round(float(np.percentile(values, 5)), 6),
        "worst_trade_pct": round(float(np.min(values)), 6),
    }


def metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    fixed = _return_metrics([float(row[TARGET]) for row in rows])
    time_stop_values = [
        (
            float(row["label_1d_net_return_pct"])
            if float(row["label_1d_net_return_pct"]) <= 0.0
            else float(row[TARGET])
        )
        for row in rows
        if row.get("label_1d_net_return_pct") is not None
    ]
    fixed["one_day_nonpositive_time_stop"] = _return_metrics(time_stop_values)
    fixed["time_stop_contract"] = (
        "exit at first-session close when net return is nonpositive; "
        "otherwise hold through fifth-session close"
    )
    return fixed


def select_rows(
    rows: Sequence[Mapping[str, Any]],
    scores: Sequence[float],
    fraction: float,
    eligibility_field: str,
) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source, score in zip(rows, scores):
        if not bool(source.get(eligibility_field)):
            continue
        row = dict(source)
        row["technical_context_score"] = float(score)
        row["entry_market_date"] = str(row["label_entry_market_date"])
        row["future_market_date"] = str(row[LABEL_END])
        by_date[str(row["market_date"])].append(row)
    candidates: list[dict[str, Any]] = []
    for day in sorted(by_date):
        ordered = sorted(
            by_date[day],
            key=lambda row: (-float(row["technical_context_score"]), str(row["symbol"])),
        )
        count = min(
            MAX_DAILY_SELECTIONS,
            max(1, int(np.ceil(len(ordered) * fraction))),
        )
        candidates.extend(ordered[:count])
    return [dict(row) for row in capacity_limited(candidates, MAX_OPEN_POSITIONS)]


def evaluate_fractions(
    rows: Sequence[Mapping[str, Any]],
    scores: Sequence[float],
    eligibility_field: str,
) -> dict[str, dict[str, Any]]:
    return {
        str(fraction): metrics(select_rows(rows, scores, fraction, eligibility_field))
        for fraction in FRACTIONS
    }


def choose_fraction(results: Mapping[str, Mapping[str, Any]]) -> float:
    eligible = [
        (float(name), result)
        for name, result in results.items()
        if int(result["count"]) >= 10
    ]
    if not eligible:
        raise ValueError("validation has fewer than ten capacity-limited selections")
    return max(
        eligible,
        key=lambda item: (
            float(item[1]["mean_net_return_pct"]),
            float(item[1]["win_rate"]),
            -item[0],
        ),
    )[0]


def train_stage(
    rows: Sequence[Mapping[str, Any]],
    stage: str,
    prefixes: Sequence[str],
    eligibility_field: str,
    output_dir: Path,
) -> dict[str, Any]:
    names = technical_feature_names(rows, prefixes)
    forbidden = [name for name in names if name.startswith("label_")]
    if forbidden:
        raise ValueError(f"future labels entered feature set: {forbidden}")
    x = matrix(rows, names)
    y = np.asarray(
        [float(row[TARGET]) >= TARGET_RETURN_PCT for row in rows],
        dtype=np.int32,
    )
    train_idx, validation_idx, test_idx, split = chronological_split(
        rows, 0.60, 0.20, 1, label_end_field=LABEL_END,
    )
    train_data = lgb.Dataset(x[train_idx], label=y[train_idx], feature_name=names)
    validation_data = lgb.Dataset(
        x[validation_idx], label=y[validation_idx],
        reference=train_data, feature_name=names,
    )
    model = lgb.train(
        {
            "objective": "binary", "metric": ["binary_logloss", "auc"],
            "learning_rate": 0.025, "num_leaves": 15, "min_data_in_leaf": 20,
            "feature_fraction": 1.0, "lambda_l1": 2.0, "lambda_l2": 8.0,
            "verbosity": -1, "seed": 42, "force_col_wise": True,
        },
        train_data,
        num_boost_round=500,
        valid_sets=[validation_data],
        callbacks=[lgb.early_stopping(40, verbose=False), lgb.log_evaluation(0)],
    )
    score = lambda indexes: model.predict(x[indexes], num_iteration=model.best_iteration)
    validation_rows = [rows[index] for index in validation_idx]
    test_rows = [rows[index] for index in test_idx]
    validation_results = evaluate_fractions(
        validation_rows, score(validation_idx), eligibility_field,
    )
    selected_fraction = choose_fraction(validation_results)
    test_results = evaluate_fractions(test_rows, score(test_idx), eligibility_field)

    stage_dir = output_dir / stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    model_path = stage_dir / "model.txt"
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
        "stage": stage,
        "eligibility_field": eligibility_field,
        "features": len(names),
        "feature_names": names,
        "best_iteration": int(model.best_iteration),
        "split": split,
        "class_rates": {
            "train": round(float(np.mean(y[train_idx])), 6),
            "validation": round(float(np.mean(y[validation_idx])), 6),
            "test": round(float(np.mean(y[test_idx])), 6),
        },
        "validation_fractions": validation_results,
        "validation_selected_fraction": selected_fraction,
        "test_at_validation_selected_fraction": test_results[str(selected_fraction)],
        "test_all_fractions_diagnostic": test_results,
        "top_features": importance[:25],
        "model_path": str(model_path),
        "model_sha256": sha256(model_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    source_rows = read_jsonl(args.input)
    rows = engineer_rows([
        row for row in source_rows
        if row.get(TARGET) is not None
        and row.get(LABEL_END)
        and row.get("label_entry_market_date")
    ])
    models = [
        train_stage(rows, stage, prefixes, eligibility, args.output_dir)
        for stage, prefixes, eligibility in STAGES
    ]
    report = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "model_family": "five-session catalyst + momentum",
        "input": str(args.input),
        "input_sha256": sha256(args.input),
        "rows": len(rows),
        "symbols": sorted({str(row["symbol"]) for row in rows}),
        "target": f"{TARGET} >= {TARGET_RETURN_PCT}",
        "entry": "next regular-session open",
        "exit": "fifth subsequent regular-session close",
        "round_trip_cost_pct": 0.25,
        "risk_contract": {
            "maximum_daily_selections": MAX_DAILY_SELECTIONS,
            "maximum_open_positions": MAX_OPEN_POSITIONS,
            "parabolic_filter": "RSI14 > 85, Bollinger position > 1.25, or EMA21 distance > 12%",
            "atr_filter_pct": [0.5, 8.0],
            "one_day_time_exit":
                "reported without selection tuning: exit first close if net return is nonpositive",
            "hard_stop_backtest":
                "deferred: panel lacks point-in-time intraday low/path data",
            "two_session_time_exit":
                "deferred: panel lacks an exact second-session exit label",
            "paper_or_live_orders": False,
        },
        "available_logic": [
            "oversold bounce, breakout, continuation, relative strength, volume confirmation",
            "target-specific news, recent earnings reaction, analyst-action proxy",
            "historical unusual call activity and option positioning",
            "recent earnings quality, insider purchases, explicit short-interest missingness",
            "ATR/parabolic risk filters and five-position correlation cap",
        ],
        "unavailable_logic": [
            "complete point-in-time upcoming earnings calendar",
            "licensed structured analyst rating and price-target history",
            "historical guidance/design-win/capacity event taxonomy",
            "intraday stop-loss and exact two-session time-stop paths",
            "portfolio-level sector correlation estimates",
        ],
        "warning":
            "This historical period was already observed; results are exploratory and require a frozen future journal.",
        "models": models,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(report_path),
        "models": len(models),
        "rows": len(rows),
    }, indent=2))


if __name__ == "__main__":
    main()
