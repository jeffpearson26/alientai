from __future__ import annotations

"""Train and prospectively score matched AI17 1m/5m five-session models."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np

from train_amd_nvda_intraday_call_five_session import matrix, read_jsonl, sha256


FEATURE_PREFIXES = (
    "1min_",
    "5min_",
    "daily_",
    "symbol_is_",
    "qqq_",
    "spy_",
    "relative_to_",
)
CALL_FEATURES = (
    "call_activity_history_count",
    "call_volume_vs_prior_median",
    "call_volume_zscore",
    "call_volume_open_interest_ratio",
    "option_call_volume",
    "option_call_open_interest",
    "option_near_money_call_iv",
    "option_contract_count",
    "option_liquid_contract_count",
)
MAX_DAILY_SELECTIONS = 5
PORTFOLIO_SLOTS = 25


def capital_scaled_drawdown(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    by_exit: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_exit[str(row["label_5d_exit_market_date"])].append(
            float(row["label_5d_net_return_pct"])
        )
    equity = peak = 1.0
    worst = 0.0
    for market_date in sorted(by_exit):
        daily = sum(by_exit[market_date]) / PORTFOLIO_SLOTS / 100.0
        equity *= 1.0 + daily
        peak = max(peak, equity)
        worst = min(worst, equity / peak - 1.0)
    return worst * 100.0


def performance(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "signals": 0,
            "decision_dates": 0,
            "mean_net_return_pct": None,
            "median_net_return_pct": None,
            "win_rate_pct": None,
            "bootstrap_mean_ci95_low_pct": None,
            "bootstrap_mean_ci95_high_pct": None,
            "capital_scaled_max_drawdown_pct": None,
        }
    values = np.asarray(
        [float(row["label_5d_net_return_pct"]) for row in rows]
    )
    values_by_date: dict[str, np.ndarray] = {}
    for market_date in sorted({str(row["market_date"]) for row in rows}):
        values_by_date[market_date] = np.asarray(
            [
                float(row["label_5d_net_return_pct"])
                for row in rows
                if str(row["market_date"]) == market_date
            ]
        )
    date_values = list(values_by_date.values())
    rng = np.random.default_rng(260805)
    bootstrap = np.asarray(
        [
            float(
                np.mean(
                    np.concatenate(
                        [
                            date_values[index]
                            for index in rng.integers(
                                0, len(date_values), size=len(date_values)
                            )
                        ]
                    )
                )
            )
            for _ in range(10000)
        ]
    )
    return {
        "signals": len(rows),
        "decision_dates": len({str(row["market_date"]) for row in rows}),
        "mean_net_return_pct": round(float(np.mean(values)), 6),
        "median_net_return_pct": round(float(np.median(values)), 6),
        "win_rate_pct": round(float(np.mean(values > 0) * 100.0), 4),
        "target_2pct_rate_pct": round(
            float(np.mean(values >= 2.0) * 100.0), 4
        ),
        "bootstrap_mean_ci95_low_pct": round(
            float(np.percentile(bootstrap, 2.5)), 6
        ),
        "bootstrap_mean_ci95_high_pct": round(
            float(np.percentile(bootstrap, 97.5)), 6
        ),
        "worst_net_return_pct": round(float(np.min(values)), 6),
        "capital_scaled_max_drawdown_pct": round(
            float(capital_scaled_drawdown(rows)), 6
        ),
        "symbol_counts": {
            symbol: sum(str(row["symbol"]) == symbol for row in rows)
            for symbol in sorted({str(row["symbol"]) for row in rows})
        },
    }


def features(rows: list[dict[str, Any]]) -> list[str]:
    names = sorted(
        {
            name
            for row in rows
            for name in row
            if name.startswith(FEATURE_PREFIXES)
        }
    )
    if not names or any("label" in name or "future" in name for name in names):
        raise ValueError("invalid feature set")
    return names


def fit_with_validation(
    params: dict[str, Any],
    train: list[dict[str, Any]],
    validation: list[dict[str, Any]],
    names: list[str],
) -> tuple[lgb.Booster, int]:
    model = lgb.train(
        params,
        lgb.Dataset(
            matrix(train, names),
            label=np.asarray(
                [float(row["label_5d_net_return_pct"]) > 0 for row in train]
            ),
            feature_name=names,
        ),
        num_boost_round=1000,
        valid_sets=[
            lgb.Dataset(
                matrix(validation, names),
                label=np.asarray(
                    [
                        float(row["label_5d_net_return_pct"]) > 0
                        for row in validation
                    ]
                ),
                feature_name=names,
            )
        ],
        callbacks=[lgb.early_stopping(80, verbose=False)],
    )
    return model, max(1, int(model.best_iteration))


def refit_model(
    params: dict[str, Any],
    rows: list[dict[str, Any]],
    names: list[str],
    iterations: int,
) -> lgb.Booster:
    return lgb.train(
        params,
        lgb.Dataset(
            matrix(rows, names),
            label=np.asarray(
                [float(row["label_5d_net_return_pct"]) > 0 for row in rows]
            ),
            feature_name=names,
        ),
        num_boost_round=iterations,
    )


def call_eligible(row: dict[str, Any]) -> bool:
    return (
        row.get("call_features_available") is True
        and int(row.get("call_activity_history_count") or 0) >= 10
        and row.get("call_volume_zscore") is not None
        and row.get("call_volume_vs_prior_median") is not None
        and row.get("option_call_volume") is not None
    )


def choose(
    rows: list[dict[str, Any]],
    probabilities: np.ndarray,
    require_calls: bool = True,
) -> list[dict[str, Any]]:
    candidates = []
    for source, probability in zip(rows, probabilities):
        if probability <= 0.5:
            continue
        if require_calls and not (
            source.get("call_features_available") is True
            and int(source.get("call_activity_history_count") or 0) >= 10
            and source.get("call_volume_unusual") is True
        ):
            continue
        candidates.append(
            {**source, "predicted_positive_probability": float(probability)}
        )
    return sorted(
        candidates,
        key=lambda row: (
            -float(row["predicted_positive_probability"]),
            str(row["symbol"]),
        ),
    )[:MAX_DAILY_SELECTIONS]


def train_one(
    panel_path: Path,
    prospective_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    rows = read_jsonl(panel_path)
    prospective = read_jsonl(prospective_path)
    technical_names = features(rows)
    call_names = technical_names + list(CALL_FEATURES)
    train = [
        row
        for row in rows
        if row["market_date"] < "2024-01-01"
        and row["label_5d_exit_market_date"] < "2024-01-01"
    ]
    validation = [
        row
        for row in rows
        if "2024-01-01" <= row["market_date"] < "2025-01-01"
        and row["label_5d_exit_market_date"] < "2025-01-01"
    ]
    refit = [
        row
        for row in rows
        if row["market_date"] < "2026-01-01"
        and row["label_5d_exit_market_date"] < "2026-01-01"
    ]
    call_train = [
        row
        for row in rows
        if call_eligible(row)
        and row["market_date"] < "2026-05-01"
        and row["label_5d_exit_market_date"] < "2026-05-01"
    ]
    call_validation = [
        row
        for row in rows
        if call_eligible(row)
        and "2026-05-01" <= row["market_date"] < "2026-06-01"
        and row["label_5d_exit_market_date"] < "2026-06-01"
    ]
    call_holdout = [
        row
        for row in rows
        if call_eligible(row) and row["market_date"] >= "2026-06-01"
    ]
    call_refit = [row for row in rows if call_eligible(row)]
    if not all(
        (
            train,
            validation,
            refit,
            call_train,
            call_validation,
            call_holdout,
            call_refit,
        )
    ):
        raise ValueError("fixed chronological partitions are incomplete")
    params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "learning_rate": 0.03,
        "num_leaves": 31,
        "max_depth": 6,
        "min_data_in_leaf": 80,
        "feature_fraction": 0.85,
        "bagging_fraction": 0.85,
        "bagging_freq": 1,
        "lambda_l1": 0.2,
        "lambda_l2": 1.0,
        "verbosity": -1,
        "seed": 260805,
        "feature_fraction_seed": 260805,
        "bagging_seed": 260805,
        "deterministic": True,
        "force_col_wise": True,
        "num_threads": 6,
    }
    _, technical_best_iteration = fit_with_validation(
        params,
        train,
        validation,
        technical_names,
    )
    technical_final = refit_model(
        params,
        refit,
        technical_names,
        technical_best_iteration,
    )
    call_fit, call_best_iteration = fit_with_validation(
        params,
        call_train,
        call_validation,
        call_names,
    )
    call_final = refit_model(
        params, call_refit, call_names, call_best_iteration
    )
    base_holdout_probabilities = technical_final.predict(
        matrix(call_holdout, technical_names),
        num_iteration=technical_best_iteration,
    )
    call_holdout_probabilities = call_fit.predict(
        matrix(call_holdout, call_names),
        num_iteration=call_best_iteration,
    )
    holdout_probabilities = (
        base_holdout_probabilities + call_holdout_probabilities
    ) / 2.0
    by_date: dict[str, list[tuple[dict[str, Any], float]]] = {}
    for row, base_probability, call_probability, probability in zip(
        call_holdout,
        base_holdout_probabilities,
        call_holdout_probabilities,
        holdout_probabilities,
    ):
        enriched = {
            **row,
            "technical_probability": float(base_probability),
            "call_aware_probability": float(call_probability),
        }
        by_date.setdefault(str(row["market_date"]), []).append(
            (enriched, float(probability))
        )
    selected = []
    eligible_dates = 0
    for market_date in sorted(by_date):
        day_rows = [item[0] for item in by_date[market_date]]
        day_probabilities = np.asarray([item[1] for item in by_date[market_date]])
        if any(
            row.get("call_features_available") is True
            and int(row.get("call_activity_history_count") or 0) >= 10
            for row in day_rows
        ):
            eligible_dates += 1
        selected.extend(choose(day_rows, day_probabilities))
    heldout_metrics = performance(selected)
    heldout_metrics["eligible_call_dates"] = eligible_dates
    heldout_metrics["abstention_rate_pct"] = round(
        (
            1.0
            - len({str(row["market_date"]) for row in selected})
            / max(eligible_dates, 1)
        )
        * 100.0,
        4,
    )
    prospective_eligible = [row for row in prospective if call_eligible(row)]
    prospective_base = (
        technical_final.predict(
            matrix(prospective_eligible, technical_names),
            num_iteration=technical_best_iteration,
        )
        if prospective_eligible
        else np.asarray([])
    )
    prospective_call = (
        call_final.predict(
            matrix(prospective_eligible, call_names),
            num_iteration=call_best_iteration,
        )
        if prospective_eligible
        else np.asarray([])
    )
    prospective_rows = [
        {
            **row,
            "technical_probability": float(base_probability),
            "call_aware_probability": float(call_probability),
        }
        for row, base_probability, call_probability in zip(
            prospective_eligible, prospective_base, prospective_call
        )
    ]
    prospective_probabilities = (prospective_base + prospective_call) / 2.0
    prospective_selected = choose(
        prospective_rows, prospective_probabilities
    )
    output_root.mkdir(parents=True, exist_ok=True)
    resolution = str(rows[0]["resolution"])
    model_path = output_root / f"ai17_{resolution}_technical_model.txt"
    call_model_path = output_root / f"ai17_{resolution}_call_aware_model.txt"
    technical_final.save_model(str(model_path))
    call_final.save_model(str(call_model_path))
    holdout_path = output_root / f"ai17_{resolution}_holdout_selections.jsonl"
    prospective_output = (
        output_root / f"ai17_{resolution}_prospective_selections.jsonl"
    )
    for path, values in (
        (holdout_path, selected),
        (prospective_output, prospective_selected),
    ):
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in values:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    status = (
        "historical_holdout_promising_not_promoted"
        if heldout_metrics["signals"] >= 30
        and heldout_metrics["decision_dates"] >= 10
        and float(heldout_metrics["mean_net_return_pct"] or 0) > 0
        and float(heldout_metrics["win_rate_pct"] or 0) >= 55
        and float(heldout_metrics["bootstrap_mean_ci95_low_pct"] or 0) > 0
        else "research_hold"
    )
    report = {
        "status": status,
        "resolution": resolution,
        "symbols": sorted({str(row["symbol"]) for row in rows}),
        "benchmarks": ["QQQ", "SPY"],
        "horizon_sessions": 5,
        "technical_feature_count": len(technical_names),
        "technical_feature_names": technical_names,
        "call_aware_feature_count": len(call_names),
        "call_aware_feature_names": call_names,
        "technical_best_iteration": technical_best_iteration,
        "call_aware_best_iteration": call_best_iteration,
        "partitions": {
            "initial_train_rows": len(train),
            "validation_rows": len(validation),
            "refit_rows": len(refit),
            "call_train_rows": len(call_train),
            "call_validation_rows": len(call_validation),
            "call_refit_rows": len(call_refit),
            "call_holdout_rows": len(call_holdout),
            "call_holdout_first": min(
                row["market_date"] for row in call_holdout
            ),
            "call_holdout_last": max(
                row["market_date"] for row in call_holdout
            ),
        },
        "historical_holdout": heldout_metrics,
        "prospective_decision_date": (
            prospective[0]["market_date"] if prospective else None
        ),
        "prospective_universe_rows": len(prospective),
        "prospective_selections": [
            {
                "symbol": row["symbol"],
                "predicted_positive_probability": round(
                    float(row["predicted_positive_probability"]), 6
                ),
                "call_volume_zscore": row["call_volume_zscore"],
                "call_activity_history_count": row[
                    "call_activity_history_count"
                ],
            }
            for row in prospective_selected
        ],
        "selection_contract": (
            "previous completed session call activity only; probability >0.50; "
            "at least 10 prior call observations; call-volume z-score >=3; "
            "zero to five selections; explicit abstention permitted"
        ),
        "panel_sha256": sha256(panel_path),
        "prospective_input_sha256": sha256(prospective_path),
        "model_sha256": sha256(model_path),
        "call_model_sha256": sha256(call_model_path),
        "research_only": True,
        "execution_enabled": False,
    }
    report_path = output_root / f"ai17_{resolution}_training_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, required=True)
    parser.add_argument("--prospective-date", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    reports = []
    for resolution in ("1min", "5min"):
        reports.append(
            train_one(
                args.panel_root / f"ai17_{resolution}_five_session_panel.jsonl",
                args.panel_root
                / f"ai17_{resolution}_{args.prospective_date}_prospective.jsonl",
                args.output_root,
            )
        )
    comparison = {
        "status": "complete",
        "models": reports,
        "research_only": True,
        "execution_enabled": False,
    }
    path = args.output_root / "comparison.json"
    path.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    main()
