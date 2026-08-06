from __future__ import annotations

"""Train and validation-gate the five-session cross-sectional picker."""

import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.research.cross_sectional_technical_5d import RANK_FEATURES


HORIZON_SESSIONS = 5
EMBARGO_SESSIONS = 5
ROUND_TRIP_COST_PCT = 0.25
MAX_DAILY_SELECTIONS = 15
PORTFOLIO_SLOTS = HORIZON_SESSIONS * MAX_DAILY_SELECTIONS
POLICY_THRESHOLDS = (0.80, 0.85)
MARKET_DATE_PATTERN = re.compile(r'"market_date"\s*:\s*"([^"]+)"')
TARGET = "label_5d_cross_sectional_return_rank"
RETURN = "label_5d_net_return_pct"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scan_dates(path: Path) -> set[str]:
    dates = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            match = MARKET_DATE_PATTERN.search(line)
            if match is None:
                raise ValueError(f"market_date missing at line {line_number}")
            dates.add(match.group(1))
    return dates


def read_dates(path: Path, allowed: set[str]) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            match = MARKET_DATE_PATTERN.search(line)
            if match is None:
                raise ValueError(f"market_date missing at line {line_number}")
            if match.group(1) in allowed:
                rows.append(json.loads(line))
    return rows


def split_dates(dates: Iterable[str]) -> dict[str, set[str]]:
    ordered = sorted(set(dates))
    if len(ordered) < 1_000:
        raise ValueError("at least 1,000 decision dates are required")
    boundaries = [
        int(len(ordered) * fraction)
        for fraction in (0.50, 0.65, 0.78, 0.90)
    ]

    def section(left: int, right: int) -> set[str]:
        start = left + EMBARGO_SESSIONS if left else 0
        end = right - EMBARGO_SESSIONS
        if end <= start:
            raise ValueError("empty split after five-session embargo")
        return set(ordered[start:end])

    train = section(0, boundaries[0])
    fit = section(boundaries[0], boundaries[1])
    calibration = section(boundaries[1], boundaries[2])
    policy = section(boundaries[2], boundaries[3])
    test = set(ordered[boundaries[3] + EMBARGO_SESSIONS :])
    assigned = train | fit | calibration | policy | test
    return {
        "train": train,
        "fit_validation": fit,
        "calibration": calibration,
        "policy_validation": policy,
        "test": test,
        "embargo": set(ordered) - assigned,
    }


def feature_names(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    available = {name for row in rows for name in row}
    names = [f"rank_{name}" for name in RANK_FEATURES]
    names.extend(
        sorted(
            name
            for name in available
            if name.startswith("market_")
        )
    )
    names.extend(
        (
            "x5_atr_14_pct",
            "x5_bollinger_width_20_pct",
            "x5_realized_volatility_10d_annualized_pct",
            "x5_realized_volatility_20d_annualized_pct",
            "x5_average_dollar_volume_20d",
            "x5_transparent_composite_score",
        )
    )
    missing = [name for name in names if name not in available]
    if missing:
        raise ValueError(f"required features missing: {missing}")
    forbidden = [
        name
        for name in names
        if name.startswith("label_") or "future" in name.lower()
    ]
    if forbidden:
        raise ValueError(f"future fields entered features: {forbidden}")
    return names


def numeric(value: Any) -> float:
    if value is None:
        return np.nan
    if isinstance(value, bool):
        return float(value)
    try:
        output = float(value)
    except (TypeError, ValueError):
        return np.nan
    return output if np.isfinite(output) else np.nan


def matrix(
    rows: Sequence[Mapping[str, Any]], names: Sequence[str]
) -> np.ndarray:
    return np.asarray(
        [[numeric(row.get(name)) for name in names] for row in rows],
        dtype=np.float32,
    )


def eligible_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows if row.get("x5_eligible") is True]


def date_local_score_percentiles(
    rows: Sequence[Mapping[str, Any]], scores: np.ndarray
) -> np.ndarray:
    output = np.full(len(rows), np.nan, dtype=float)
    groups: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        groups[str(row["market_date"])].append(index)
    for indices in groups.values():
        ordered = sorted(
            indices,
            key=lambda index: (float(scores[index]), str(rows[index]["symbol"])),
        )
        values = np.asarray([float(scores[index]) for index in ordered])
        positions = np.linspace(0.0, 1.0, len(ordered))
        start = 0
        while start < len(ordered):
            end = start + 1
            while end < len(ordered) and np.isclose(
                values[end], values[start], rtol=0.0, atol=1e-12
            ):
                end += 1
            rank = float(np.mean(positions[start:end]))
            for index in ordered[start:end]:
                output[index] = rank
            start = end
    return output


def select_rows(
    rows: Sequence[Mapping[str, Any]],
    raw_scores: np.ndarray,
    threshold: float,
    *,
    highest: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    percentiles = date_local_score_percentiles(rows, raw_scores)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row, raw, percentile in zip(rows, raw_scores, percentiles):
        qualifies = (
            percentile >= threshold
            if highest
            else percentile <= 1.0 - threshold
        )
        if not qualifies:
            continue
        item = dict(row)
        item["model_score"] = float(raw)
        item["model_score_cross_sectional_percentile"] = float(percentile)
        groups[str(row["market_date"])].append(item)
    output = []
    tie_abstentions = 0
    for market_date in sorted(groups):
        ranked = sorted(
            groups[market_date],
            key=lambda row: (
                -float(row["model_score"])
                if highest
                else float(row["model_score"]),
                str(row["symbol"]),
            ),
        )
        if (
            len(ranked) > MAX_DAILY_SELECTIONS
            and np.isclose(
                float(ranked[MAX_DAILY_SELECTIONS - 1]["model_score"]),
                float(ranked[MAX_DAILY_SELECTIONS]["model_score"]),
                rtol=0.0,
                atol=1e-12,
            )
        ):
            tie_abstentions += 1
            continue
        output.extend(ranked[:MAX_DAILY_SELECTIONS])
    return output, {
        "selected_dates": len(groups) - tie_abstentions,
        "boundary_tie_abstentions": tie_abstentions,
    }


def daily_portfolio_pnl_pct(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    """Fixed-slot, idle-cash-aware daily P/L from exact holding paths."""
    daily_pnl_pct: dict[str, float] = defaultdict(float)
    for row in rows:
        previous = 0.0
        path = row.get("label_5d_mark_to_market_path") or []
        if len(path) != HORIZON_SESSIONS:
            raise ValueError("selected row lacks exact five-session path")
        for index, point in enumerate(path):
            gross = float(point["gross_return_from_entry_pct"])
            increment = gross - previous
            if index == HORIZON_SESSIONS - 1:
                increment -= float(row["round_trip_cost_pct"])
            daily_pnl_pct[str(point["market_date"])] += (
                increment / PORTFOLIO_SLOTS
            )
            previous = gross
    return dict(daily_pnl_pct)


def mark_to_market_drawdown(rows: Sequence[Mapping[str, Any]]) -> float | None:
    """Fixed-slot, idle-cash-aware drawdown from exact five-session paths."""
    if not rows:
        return None
    daily_pnl_pct = daily_portfolio_pnl_pct(rows)
    equity = peak = 1.0
    worst = 0.0
    for market_date in sorted(daily_pnl_pct):
        equity += daily_pnl_pct[market_date] / 100.0
        peak = max(peak, equity)
        worst = min(worst, (equity / peak - 1.0) * 100.0)
    return float(worst)


def rank_ic(
    rows: Sequence[Mapping[str, Any]], scores: np.ndarray
) -> dict[str, Any]:
    score_ranks = date_local_score_percentiles(rows, scores)
    groups: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        groups[str(row["market_date"])].append(index)
    values = []
    for indices in groups.values():
        if len(indices) < 5:
            continue
        x = np.asarray([float(score_ranks[index]) for index in indices])
        y = np.asarray(
            [float(rows[index][TARGET]) for index in indices], dtype=float
        )
        if np.std(x) <= 0.0 or np.std(y) <= 0.0:
            continue
        values.append(float(np.corrcoef(x, y)[0, 1]))
    return {
        "date_count": len(values),
        "mean_spearman_rank_ic": (
            None if not values else float(np.mean(values))
        ),
        "median_spearman_rank_ic": (
            None if not values else float(np.median(values))
        ),
    }


def metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "count": 0,
            "distinct_market_dates": 0,
            "mean_net_return_pct": None,
            "median_net_return_pct": None,
            "win_rate": None,
            "fifth_percentile_pct": None,
            "worst_trade_pct": None,
            "capital_scaled_max_drawdown_pct": None,
            "capital_scaled_annualized_sharpe": None,
        }
    returns = np.asarray([float(row[RETURN]) for row in rows], dtype=float)
    daily_pnl = np.asarray(
        list(daily_portfolio_pnl_pct(rows).values()), dtype=float
    )
    sharpe = (
        None
        if len(daily_pnl) < 2 or float(np.std(daily_pnl, ddof=1)) <= 0.0
        else float(
            np.mean(daily_pnl)
            / np.std(daily_pnl, ddof=1)
            * np.sqrt(252.0)
        )
    )
    return {
        "count": len(rows),
        "distinct_market_dates": len(
            {str(row["market_date"]) for row in rows}
        ),
        "mean_net_return_pct": float(np.mean(returns)),
        "median_net_return_pct": float(np.median(returns)),
        "win_rate": float(np.mean(returns > 0.0)),
        "fifth_percentile_pct": float(np.percentile(returns, 5.0)),
        "worst_trade_pct": float(np.min(returns)),
        "capital_scaled_max_drawdown_pct": mark_to_market_drawdown(rows),
        "capital_scaled_annualized_sharpe": sharpe,
    }


def nonoverlap_metrics(
    selected: Sequence[Mapping[str, Any]], all_dates: Sequence[str]
) -> dict[str, Any]:
    date_index = {value: index for index, value in enumerate(all_dates)}
    rotations = {}
    for rotation in range(HORIZON_SESSIONS):
        rows = [
            row
            for row in selected
            if date_index[str(row["market_date"])] % HORIZON_SESSIONS
            == rotation
        ]
        rotations[str(rotation)] = metrics(rows)
    return rotations


def evaluate_policy(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    threshold: float,
    all_dates: Sequence[str],
) -> dict[str, Any]:
    selected, diagnostics = select_rows(rows, scores, threshold)
    bottom, bottom_diagnostics = select_rows(
        rows, scores, threshold, highest=False
    )
    top_metrics = metrics(selected)
    bottom_metrics = metrics(bottom)
    top_metrics["rank_ic"] = rank_ic(rows, scores)
    top_metrics["matched_bottom"] = bottom_metrics
    top_metrics["top_minus_bottom_mean_net_pct"] = (
        None
        if top_metrics["mean_net_return_pct"] is None
        or bottom_metrics["mean_net_return_pct"] is None
        else float(
            top_metrics["mean_net_return_pct"]
            - bottom_metrics["mean_net_return_pct"]
        )
    )
    top_metrics["selection_diagnostics"] = diagnostics
    top_metrics["bottom_selection_diagnostics"] = bottom_diagnostics
    top_metrics["nonoverlap_rotations"] = nonoverlap_metrics(
        selected, all_dates
    )
    return top_metrics


def validation_score(result: Mapping[str, Any]) -> float:
    if (
        int(result["count"]) < 100
        or int(result["distinct_market_dates"]) < 20
        or result["mean_net_return_pct"] is None
        or result["median_net_return_pct"] is None
        or result["top_minus_bottom_mean_net_pct"] is None
        or result["rank_ic"]["mean_spearman_rank_ic"] is None
    ):
        return -math.inf
    return float(
        result["mean_net_return_pct"]
        + 0.5 * result["median_net_return_pct"]
        + 0.5 * result["top_minus_bottom_mean_net_pct"]
        + 5.0 * result["rank_ic"]["mean_spearman_rank_ic"]
    )


def policy_gate(result: Mapping[str, Any]) -> tuple[bool, list[str]]:
    failures = []
    requirements = (
        ("minimum_100_trades", int(result["count"]) >= 100),
        (
            "minimum_20_dates",
            int(result["distinct_market_dates"]) >= 20,
        ),
        (
            "positive_mean",
            result["mean_net_return_pct"] is not None
            and float(result["mean_net_return_pct"]) > 0.0,
        ),
        (
            "positive_median",
            result["median_net_return_pct"] is not None
            and float(result["median_net_return_pct"]) > 0.0,
        ),
        (
            "at_least_half_winners",
            result["win_rate"] is not None
            and float(result["win_rate"]) >= 0.50,
        ),
        (
            "positive_rank_ic",
            result["rank_ic"]["mean_spearman_rank_ic"] is not None
            and float(result["rank_ic"]["mean_spearman_rank_ic"]) >= 0.01,
        ),
        (
            "beats_bottom_control",
            result["top_minus_bottom_mean_net_pct"] is not None
            and float(result["top_minus_bottom_mean_net_pct"]) > 0.0,
        ),
        (
            "drawdown_above_minus_20",
            result["capital_scaled_max_drawdown_pct"] is not None
            and float(result["capital_scaled_max_drawdown_pct"]) > -20.0,
        ),
    )
    for name, passed in requirements:
        if not passed:
            failures.append(name)
    return not failures, failures


def score_rows(
    variant: str,
    rows: Sequence[Mapping[str, Any]],
    booster: lgb.Booster,
    names: Sequence[str],
) -> np.ndarray:
    if variant == "transparent":
        return np.asarray(
            [float(row["x5_transparent_composite_score"]) for row in rows],
            dtype=float,
        )
    if variant != "lightgbm":
        raise ValueError(f"unknown variant: {variant}")
    return np.asarray(
        booster.predict(matrix(rows, names), num_iteration=booster.best_iteration),
        dtype=float,
    )


def date_range(values: set[str]) -> dict[str, Any]:
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "first": ordered[0] if ordered else None,
        "last": ordered[-1] if ordered else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--panel-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise ValueError("output root must be new and empty")
    manifest = json.loads(args.panel_manifest.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "complete"
        or int(manifest.get("horizon_sessions", 0)) != HORIZON_SESSIONS
        or int(manifest.get("candidate_count", 0)) != 104
        or manifest.get("panel_sha256") != sha256(args.panel)
    ):
        raise ValueError("panel manifest contract mismatch")

    all_dates = scan_dates(args.panel)
    split = split_dates(all_dates)
    pretest_dates = (
        split["train"]
        | split["fit_validation"]
        | split["calibration"]
        | split["policy_validation"]
    )
    pretest = read_dates(args.panel, pretest_dates)
    groups = {
        name: eligible_rows(
            [
                row
                for row in pretest
                if str(row["market_date"]) in split[name]
            ]
        )
        for name in (
            "train",
            "fit_validation",
            "calibration",
            "policy_validation",
        )
    }
    names = feature_names(groups["train"])
    train_x = matrix(groups["train"], names)
    fit_x = matrix(groups["fit_validation"], names)
    train_y = np.asarray(
        [float(row[TARGET]) for row in groups["train"]], dtype=float
    )
    fit_y = np.asarray(
        [float(row[TARGET]) for row in groups["fit_validation"]], dtype=float
    )
    model = lgb.LGBMRegressor(
        objective="regression_l2",
        n_estimators=2_000,
        learning_rate=0.025,
        num_leaves=31,
        min_child_samples=100,
        subsample=0.80,
        colsample_bytree=0.80,
        reg_alpha=0.25,
        reg_lambda=1.0,
        random_state=20260805,
        deterministic=True,
        force_col_wise=True,
        n_jobs=-1,
        verbosity=-1,
    )
    model.fit(
        train_x,
        train_y,
        eval_set=[(fit_x, fit_y)],
        eval_metric="l2",
        callbacks=[lgb.early_stopping(100, verbose=False)],
    )
    booster = model.booster_
    args.output_root.mkdir(parents=True, exist_ok=True)
    model_path = args.output_root / "model.txt"
    booster.save_model(str(model_path))

    calibration_dates = sorted(split["calibration"])
    candidates = []
    for variant in ("transparent", "lightgbm"):
        scores = score_rows(
            variant, groups["calibration"], booster, names
        )
        for threshold in POLICY_THRESHOLDS:
            result = evaluate_policy(
                groups["calibration"],
                scores,
                threshold,
                calibration_dates,
            )
            candidates.append(
                {
                    "variant": variant,
                    "threshold": threshold,
                    "validation_score": validation_score(result),
                    "metrics": result,
                }
            )
    eligible_candidates = [
        item
        for item in candidates
        if np.isfinite(float(item["validation_score"]))
    ]
    if not eligible_candidates:
        raise ValueError("no calibration policy met minimum evidence")
    chosen = max(
        eligible_candidates,
        key=lambda item: (
            float(item["validation_score"]),
            item["variant"] == "transparent",
            -float(item["threshold"]),
        ),
    )

    policy_scores = score_rows(
        str(chosen["variant"]),
        groups["policy_validation"],
        booster,
        names,
    )
    policy_result = evaluate_policy(
        groups["policy_validation"],
        policy_scores,
        float(chosen["threshold"]),
        sorted(split["policy_validation"]),
    )
    passed, failures = policy_gate(policy_result)
    report: dict[str, Any] = {
        "status": "RESEARCH_CANDIDATE" if passed else "RESEARCH_HOLD",
        "research_only": True,
        "execution_enabled": False,
        "model_id": "nasdaq_ai_cross_sectional_technical_5d_v1",
        "universe": "Nasdaq-101 union AI/semi-17 = 104 candidates",
        "horizon_sessions": HORIZON_SESSIONS,
        "entry": "next adjusted regular-session open",
        "exit": "fifth subsequent adjusted regular-session close",
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        "maximum_daily_selections": MAX_DAILY_SELECTIONS,
        "portfolio_slots": PORTFOLIO_SLOTS,
        "panel": str(args.panel),
        "panel_sha256": sha256(args.panel),
        "panel_manifest": str(args.panel_manifest),
        "panel_manifest_sha256": sha256(args.panel_manifest),
        "feature_names": names,
        "feature_count": len(names),
        "model_path": str(model_path),
        "model_sha256": sha256(model_path),
        "lightgbm_best_iteration": booster.best_iteration,
        "split": {
            name: date_range(values)
            for name, values in split.items()
        },
        "split_contract": (
            "whole decision dates; independent train, fit-validation, "
            "calibration, policy-validation, sealed-test stages; two-sided "
            "five-session embargo at every pre-test boundary"
        ),
        "calibration_candidates": candidates,
        "chosen_policy": {
            "variant": chosen["variant"],
            "top_fraction": 1.0 - float(chosen["threshold"]),
            "score_percentile_threshold": chosen["threshold"],
            "maximum_positions": MAX_DAILY_SELECTIONS,
            "chosen_from": "calibration only",
        },
        "policy_validation": policy_result,
        "policy_gate": {
            "passed": passed,
            "failures": failures,
        },
        "sealed_test": {
            "status": "UNOPENED",
            "reason": (
                "policy validation failed; labels remain unread"
                if not passed
                else "policy passed; test will be opened exactly once"
            ),
        },
        "known_limitations": [
            "fixed contemporary universe has survivorship and selection bias",
            "complete point-in-time earnings-calendar history is unavailable, so the optional earnings exclusion is absent",
            "ROC(10) duplicates 10-session return in the supplied transparent formula",
            "historical passage cannot authorize execution; future-only evidence remains required",
        ],
    }
    if passed:
        test_rows = eligible_rows(read_dates(args.panel, split["test"]))
        test_scores = score_rows(
            str(chosen["variant"]), test_rows, booster, names
        )
        report["sealed_test"] = {
            "status": "OPENED_ONCE",
            "metrics": evaluate_policy(
                test_rows,
                test_scores,
                float(chosen["threshold"]),
                sorted(split["test"]),
            ),
        }
    report_path = args.output_root / "training_report.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "output": str(report_path),
                "chosen_policy": report["chosen_policy"],
                "policy_gate": report["policy_gate"],
                "sealed_test_status": report["sealed_test"]["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
