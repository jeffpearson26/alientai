from __future__ import annotations

"""Compare technical, premarket, and combined matched-case discovery models."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np

from alientai_v2.research.matched_winner_study import DEFAULT_ANALYSIS_FEATURES
from train_matched_winner_lightgbm import (
    event_balancing_weights,
    prepare_matrix,
    read_jsonl,
    score_metrics,
    train_model,
)
from train_v2_transformer_20day_sp500_from_supabase import chronological_three_way_indices, now_iso


PREMARKET_FEATURES = [
    "premarket_bar_count", "premarket_gap_pct", "premarket_session_return_pct",
    "premarket_high_vs_previous_close_pct", "premarket_low_vs_previous_close_pct",
    "premarket_range_pct", "premarket_return_30m_pct", "premarket_return_60m_pct",
    "premarket_volume", "premarket_typical_prior_volume", "premarket_relative_volume",
    "premarket_dollar_volume", "premarket_vwap", "premarket_last_vs_vwap_pct",
]


def has_standard_open_entry_session(label: Mapping[str, Any]) -> bool:
    """Accept only labels with the intended 09:30-to-16:00 regular session bars."""
    market_date = str(label.get("market_date") or "")
    future_market_date = str(label.get("future_market_date") or "")
    return (
        bool(market_date)
        and bool(future_market_date)
        and str(label.get("premarket_entry_bar_et") or "") == f"{market_date} 09:30:00"
        and str(label.get("premarket_exit_bar_et") or "") == f"{future_market_date} 16:00:00"
    )


def identity(row: Mapping[str, Any]) -> Tuple[str, str, str, str]:
    return (
        str(row.get("study_event_id") or ""), str(row.get("study_role") or ""),
        str(row.get("symbol") or ""), str(row.get("market_date") or ""),
    )


def join_feature_rows(
    base_rows: Sequence[Mapping[str, Any]], feature_rows: Iterable[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    index: Dict[Tuple[str, str, str, str], Mapping[str, Any]] = {}
    for row in feature_rows:
        key = identity(row)
        if key in index:
            raise ValueError(f"duplicate premarket feature identity: {key}")
        index[key] = row
    joined: List[Dict[str, Any]] = []
    matched = available = 0
    for source in base_rows:
        row = dict(source)
        feature = index.get(identity(source))
        if feature is not None:
            matched += 1
            available += int(bool(feature.get("premarket_available")))
            for name in PREMARKET_FEATURES:
                row[name] = feature.get(name)
        else:
            for name in PREMARKET_FEATURES:
                row[name] = None
        joined.append(row)
    return joined, {
        "base_rows": len(base_rows), "matched_feature_rows": matched,
        "premarket_available_rows": available,
        "premarket_coverage_pct": round(100.0 * available / max(1, len(base_rows)), 6),
    }


def join_open_entry_labels(
    base_rows: Sequence[Mapping[str, Any]], label_rows: Iterable[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    index: Dict[Tuple[str, str, str, str], Mapping[str, Any]] = {}
    for row in label_rows:
        key = identity(row)
        if key in index:
            raise ValueError(f"duplicate premarket label identity: {key}")
        index[key] = row
    output = []
    nonstandard_session_labels = 0
    for source in base_rows:
        label = index.get(identity(source))
        if label is None or not bool(label.get("premarket_label_available")):
            continue
        if not has_standard_open_entry_session(label):
            nonstandard_session_labels += 1
            continue
        row = dict(source)
        row["study_label"] = int(bool(label.get("premarket_label_exceptional_winner")))
        row["label_forward_return_5d_pct"] = label.get("premarket_forward_return_5d_pct")
        row["premarket_entry_price"] = label.get("premarket_entry_price")
        row["premarket_exit_price"] = label.get("premarket_exit_price")
        output.append(row)
    return output, {
        "base_rows": len(base_rows), "tradable_label_rows": len(output),
        "excluded_nonstandard_session_labels": nonstandard_session_labels,
        "tradable_label_coverage_pct": round(100.0 * len(output) / max(1, len(base_rows)), 6),
        "exceptional_winner_rate_pct": round(
            100.0 * sum(int(row["study_label"]) for row in output) / max(1, len(output)), 6,
        ),
    }


def technical_features() -> List[str]:
    return [
        name for name in DEFAULT_ANALYSIS_FEATURES
        if name.startswith("technical_") or name.startswith("return_") or name == "realized_volatility_20d_pct"
    ]


def varying_features(rows: Sequence[Mapping[str, Any]], requested: Sequence[str]) -> List[str]:
    output = []
    for name in requested:
        if name.startswith("label_"):
            raise ValueError("future outcome labels cannot be model features")
        values = {str(row.get(name)) for row in rows if row.get(name) is not None}
        if len(values) > 1:
            output.append(name)
    return output


def ranked_return_slices(
    rows: Sequence[Mapping[str, Any]], indices: np.ndarray, scores: np.ndarray,
    round_trip_cost_pct: float,
) -> List[Dict[str, Any]]:
    if len(indices) != len(scores):
        raise ValueError("indices and scores must be aligned")
    order = np.argsort(-scores)
    output = []
    for fraction in (0.01, 0.05, 0.10):
        count = max(1, int(len(order) * fraction))
        selected = [rows[int(indices[position])] for position in order[:count]]
        net = np.asarray([
            float(row["label_forward_return_5d_pct"]) - round_trip_cost_pct for row in selected
        ], dtype=float)
        output.append({
            "fraction": fraction, "signals": len(selected),
            "symbols": len({str(row.get("symbol") or "") for row in selected}),
            "exceptional_winner_rate": round(float(np.mean([
                int(row.get("study_label") or 0) for row in selected
            ])), 6),
            "mean_net_return_pct": round(float(np.mean(net)), 6),
            "median_net_return_pct": round(float(np.median(net)), 6),
            "win_rate_after_cost": round(float(np.mean(net > 0)), 6),
            "fifth_percentile_net_return_pct": round(float(np.percentile(net, 5)), 6),
            "worst_net_return_pct": round(float(np.min(net)), 6),
        })
    return output


def promotion_gate(
    experiments: Sequence[Mapping[str, Any]], fraction: float = 0.01,
    minimum_signals: int = 30,
) -> Dict[str, Any]:
    by_name = {str(item.get("name")): item for item in experiments}
    baseline = by_name.get("technical_only")
    combined = by_name.get("technical_plus_premarket")
    checks = []
    for partition in ("validation", "test"):
        key = f"{partition}_return_slices"
        baseline_slice = next(
            (row for row in (baseline or {}).get(key, []) if float(row.get("fraction", -1)) == fraction), None,
        )
        combined_slice = next(
            (row for row in (combined or {}).get(key, []) if float(row.get("fraction", -1)) == fraction), None,
        )
        if baseline_slice is None or combined_slice is None:
            checks.append({"partition": partition, "passed": False, "reason": "required slice missing"})
            continue
        conditions = {
            "minimum_signals": int(combined_slice["signals"]) >= minimum_signals,
            "exceptional_rate_improved": (
                float(combined_slice["exceptional_winner_rate"])
                > float(baseline_slice["exceptional_winner_rate"])
            ),
            "mean_net_return_improved": (
                float(combined_slice["mean_net_return_pct"])
                > float(baseline_slice["mean_net_return_pct"])
            ),
            "median_net_return_positive": float(combined_slice["median_net_return_pct"]) > 0.0,
            "fifth_percentile_not_worse": (
                float(combined_slice["fifth_percentile_net_return_pct"])
                >= float(baseline_slice["fifth_percentile_net_return_pct"])
            ),
        }
        checks.append({
            "partition": partition, "passed": all(conditions.values()),
            "conditions": conditions, "baseline": baseline_slice, "combined": combined_slice,
        })
    passed = len(checks) == 2 and all(bool(item.get("passed")) for item in checks)
    return {
        "status": "RESEARCH_PASS" if passed else "RESEARCH_HOLD",
        "execution_enabled": False, "fraction": fraction,
        "minimum_signals": minimum_signals, "checks": checks,
        "note": "Passing permits deeper natural-universe evaluation only; it never enables trading.",
    }


def fit_experiment(
    name: str, rows: Sequence[Mapping[str, Any]], requested_features: Sequence[str],
    weights: np.ndarray, train_idx: np.ndarray, validation_idx: np.ndarray, test_idx: np.ndarray,
    output_dir: Path, num_boost_round: int, early_stopping_rounds: int,
    round_trip_cost_pct: float,
) -> Dict[str, Any]:
    features = varying_features(rows, requested_features)
    if not features:
        raise ValueError(f"{name} has no varying features")
    x, y, _, names = prepare_matrix(rows, features)
    model = train_model(
        x, y, weights, train_idx, validation_idx, names,
        num_boost_round, early_stopping_rounds,
    )
    predict = lambda indices: model.predict(x[indices], num_iteration=model.best_iteration)
    destination = output_dir / f"{name}.txt"
    model.save_model(str(destination), num_iteration=model.best_iteration)
    importance = sorted(
        ({"feature": feature, "gain": float(gain)} for feature, gain in zip(
            names, model.feature_importance(importance_type="gain"),
        )), key=lambda row: row["gain"], reverse=True,
    )
    return {
        "name": name, "requested_features": list(requested_features),
        "model_features": names, "best_iteration": int(model.best_iteration),
        "train_metrics": score_metrics(y[train_idx], predict(train_idx)),
        "validation_metrics": score_metrics(y[validation_idx], predict(validation_idx)),
        "test_metrics": score_metrics(y[test_idx], predict(test_idx)),
        "validation_return_slices": ranked_return_slices(
            rows, validation_idx, predict(validation_idx), round_trip_cost_pct,
        ),
        "test_return_slices": ranked_return_slices(
            rows, test_idx, predict(test_idx), round_trip_cost_pct,
        ),
        "top_features": importance[:30], "model_path": str(destination),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rows", type=Path, required=True)
    parser.add_argument("--premarket-features", type=Path, required=True)
    parser.add_argument("--premarket-labels", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--train-fraction", type=float, default=0.60)
    parser.add_argument("--validation-fraction", type=float, default=0.20)
    parser.add_argument("--embargo-calendar-days", type=int, default=12)
    parser.add_argument("--num-boost-round", type=int, default=1000)
    parser.add_argument("--early-stopping-rounds", type=int, default=75)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()

    labeled_rows, label_coverage = join_open_entry_labels(
        read_jsonl(args.base_rows), read_jsonl(args.premarket_labels),
    )
    rows, coverage = join_feature_rows(labeled_rows, read_jsonl(args.premarket_features))
    _, _, timestamps, _ = prepare_matrix(rows, [])
    train_idx, validation_idx, test_idx, split = chronological_three_way_indices(
        timestamps, train_fraction=args.train_fraction,
        validation_fraction=args.validation_fraction,
        embargo_calendar_days=args.embargo_calendar_days,
    )
    weights = event_balancing_weights(rows)
    groups = {
        "technical_only": technical_features(),
        "premarket_only": PREMARKET_FEATURES,
        "technical_plus_premarket": technical_features() + PREMARKET_FEATURES,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    experiments = [
        fit_experiment(
            name, rows, features, weights, train_idx, validation_idx, test_idx,
            args.output_dir, args.num_boost_round, args.early_stopping_rounds,
            args.round_trip_cost_pct,
        )
        for name, features in groups.items()
    ]
    report = {
        "status": "complete", "finished_at": now_iso(), "research_only": True,
        "execution_enabled": False, "score_is_real_world_probability": False,
        "warning": "Matched case-control scores are for feature-family comparison only; natural-universe calibration is required.",
        "round_trip_cost_pct": args.round_trip_cost_pct,
        "base_rows": str(args.base_rows), "premarket_features": str(args.premarket_features),
        "premarket_labels": str(args.premarket_labels),
        "label_coverage": label_coverage, "feature_coverage": coverage,
        "split": split, "experiments": experiments,
        "premarket_promotion_gate": promotion_gate(experiments),
    }
    path = args.output_dir / "premarket_ablation_report.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
