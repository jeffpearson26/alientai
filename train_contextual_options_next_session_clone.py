from __future__ import annotations

"""Train/evaluate the isolated contextual unusual-call one-session clone."""

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable, Iterable, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.features.insider_purchase_features import safe_float


DATE_PATTERN = re.compile(rb'"market_date":"(\d{4}-\d{2}-\d{2})"')
CONTRACT_PATTERN = re.compile(rb'"option_contract_count":([0-9]+)')
TARGET = "label_forward_return_1d_pct"
MINIMUM_DAILY_UNIVERSE = 400
MAXIMUM_DAILY_SELECTIONS = 5
TOP_FRACTION = 0.25


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scan_panel_structure(path: Path) -> dict[str, Any]:
    """Scan dates and option coverage without decoding any outcome labels."""
    daily_rows: Counter[str] = Counter()
    option_rows: Counter[str] = Counter()
    with path.open("rb") as handle:
        for line in handle:
            match = DATE_PATTERN.search(line)
            if match is None:
                raise ValueError("panel row is missing compact market_date")
            market_date = match.group(1).decode("ascii")
            daily_rows[market_date] += 1
            contracts = CONTRACT_PATTERN.search(line)
            if (
                b'"option_chain_available":true' in line
                and contracts is not None
                and int(contracts.group(1)) > 0
            ):
                option_rows[market_date] += 1
    dates = sorted(daily_rows)
    eligible_option_dates = sorted(
        day
        for day, count in option_rows.items()
        if count >= MINIMUM_DAILY_UNIVERSE
    )
    if not dates or len(eligible_option_dates) < 20:
        raise ValueError("panel lacks sufficient dates or complete option dates")
    return {
        "dates": dates,
        "eligible_option_dates": eligible_option_dates,
        "daily_rows": dict(daily_rows),
        "option_rows": dict(option_rows),
    }


def split_dates(structure: Mapping[str, Any]) -> dict[str, list[str]]:
    """Create technical-fit, policy, embargo, and sealed-test date sets."""
    all_dates = list(structure["dates"])
    option_dates = list(structure["eligible_option_dates"])
    policy_count = max(10, int(len(option_dates) * 0.60))
    if policy_count >= len(option_dates):
        raise ValueError("option split leaves no sealed test")
    policy_dates = option_dates[:policy_count]
    policy_start = policy_dates[0]
    policy_end = policy_dates[-1]

    before_policy = [day for day in all_dates if day < policy_start]
    if len(before_policy) < 40:
        raise ValueError("insufficient pre-policy dates for model fitting")
    train_count = int(len(before_policy) * 0.75)
    train_dates = before_policy[:train_count]
    # One full decision session is embargoed because each label ends at the
    # next session close.
    fit_dates = before_policy[train_count + 1 :]
    if not train_dates or not fit_dates:
        raise ValueError("technical split produced an empty partition")

    policy_end_index = all_dates.index(policy_end)
    if policy_end_index + 2 >= len(all_dates):
        raise ValueError("policy split leaves no post-embargo test")
    test_start = all_dates[policy_end_index + 2]
    test_dates = [day for day in option_dates if day >= test_start]
    if not test_dates:
        raise ValueError("sealed test has no complete option dates")
    embargo_dates = [
        day for day in all_dates if policy_end < day < test_start
    ]
    return {
        "technical_train": train_dates,
        "technical_fit_validation": fit_dates,
        "policy_validation": policy_dates,
        "policy_test_embargo": embargo_dates,
        "sealed_test": test_dates,
    }


def read_rows_for_dates(
    path: Path, selected_dates: Iterable[str]
) -> list[dict[str, Any]]:
    """Decode only requested rows; all other labels remain physically unread."""
    wanted = set(selected_dates)
    output = []
    with path.open("rb") as handle:
        for line in handle:
            match = DATE_PATTERN.search(line)
            if match is None:
                raise ValueError("panel row is missing compact market_date")
            if match.group(1).decode("ascii") not in wanted:
                continue
            output.append(json.loads(line))
    return output


def technical_feature_names(
    rows: Sequence[Mapping[str, Any]],
) -> list[str]:
    names = sorted(
        {
            name
            for row in rows
            for name in row
            if name.startswith("technical_")
        }
    )
    usable = [
        name
        for name in names
        if len(
            {
                safe_float(row.get(name))
                for row in rows
                if row.get(name) is not None
            }
        )
        > 1
    ]
    if not usable:
        raise ValueError("no nonconstant technical features")
    return usable


def matrix(
    rows: Sequence[Mapping[str, Any]], names: Sequence[str]
) -> np.ndarray:
    return np.column_stack(
        [
            np.asarray(
                [safe_float(row.get(name)) for row in rows],
                dtype=np.float32,
            )
            for name in names
        ]
    )


def eligible_context_row(row: Mapping[str, Any]) -> bool:
    return bool(
        row.get("option_chain_available")
        and safe_float(row.get("option_contract_count")) > 0
        and row.get(TARGET) is not None
    )


def choose_daily_candidates(
    rows: Sequence[Mapping[str, Any]],
    scores: Sequence[float],
    *,
    minimum_daily_universe: int = MINIMUM_DAILY_UNIVERSE,
    top_fraction: float = TOP_FRACTION,
    maximum_daily_selections: int = MAXIMUM_DAILY_SELECTIONS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply the immutable daily top-quarter plus unusual-call rule."""
    if len(rows) != len(scores):
        raise ValueError("row/score length mismatch")
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row, score in zip(rows, scores):
        if not eligible_context_row(row):
            continue
        by_date[str(row["market_date"])].append(
            {**row, "technical_context_score": float(score)}
        )
    selected: list[dict[str, Any]] = []
    daily_audit: list[dict[str, Any]] = []
    for day in sorted(by_date):
        universe = by_date[day]
        if len(universe) < minimum_daily_universe:
            daily_audit.append(
                {
                    "market_date": day,
                    "state": "INCOMPLETE_UNIVERSE",
                    "universe_rows": len(universe),
                    "selected": 0,
                }
            )
            continue
        cutoff = float(
            np.quantile(
                [row["technical_context_score"] for row in universe],
                1.0 - top_fraction,
            )
        )
        candidates = sorted(
            (
                row
                for row in universe
                if row.get("call_volume_unusual")
                and row["technical_context_score"] >= cutoff
            ),
            key=lambda row: (
                -float(row["technical_context_score"]),
                str(row["symbol"]),
            ),
        )
        picks = candidates[:maximum_daily_selections]
        selected.extend(picks)
        daily_audit.append(
            {
                "market_date": day,
                "state": "COMPLETE",
                "universe_rows": len(universe),
                "technical_top_quarter_cutoff": cutoff,
                "unusual_candidates_in_top_quarter": len(candidates),
                "selected": len(picks),
            }
        )
    return selected, daily_audit


def selection_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = [float(row[TARGET]) for row in rows]
    dates = sorted({str(row["market_date"]) for row in rows})
    symbols = Counter(str(row["symbol"]) for row in rows)
    daily = defaultdict(list)
    for row in rows:
        daily[str(row["market_date"])].append(float(row[TARGET]))
    equity = 1.0
    peak = 1.0
    worst_drawdown = 0.0
    for day in sorted(daily):
        equity *= 1.0 + mean(daily[day]) / 100.0
        peak = max(peak, equity)
        worst_drawdown = min(
            worst_drawdown, (equity / peak - 1.0) * 100.0
        )
    return {
        "signals": len(values),
        "decision_dates": len(dates),
        "first_decision_date": dates[0] if dates else None,
        "last_decision_date": dates[-1] if dates else None,
        "mean_net_return_pct": round(mean(values), 6) if values else None,
        "median_net_return_pct": (
            round(median(values), 6) if values else None
        ),
        "win_rate_pct": (
            round(mean(value > 0.0 for value in values) * 100.0, 4)
            if values
            else None
        ),
        "worst_net_return_pct": round(min(values), 6) if values else None,
        "best_net_return_pct": round(max(values), 6) if values else None,
        "daily_basket_compounded_return_pct": (
            round((equity - 1.0) * 100.0, 6) if values else None
        ),
        "daily_basket_max_drawdown_pct": (
            round(worst_drawdown, 6) if values else None
        ),
        "maximum_symbol_share_pct": (
            round(max(symbols.values()) / len(values) * 100.0, 4)
            if values
            else None
        ),
    }


def evidence_gate(metrics: Mapping[str, Any]) -> dict[str, Any]:
    checks = {
        "minimum_30_signals": int(metrics.get("signals") or 0) >= 30,
        "minimum_10_decision_dates": (
            int(metrics.get("decision_dates") or 0) >= 10
        ),
        "positive_mean_net_return": (
            float(metrics.get("mean_net_return_pct") or 0.0) > 0.0
        ),
        "positive_median_net_return": (
            float(metrics.get("median_net_return_pct") or 0.0) > 0.0
        ),
        "minimum_50pct_win_rate": (
            float(metrics.get("win_rate_pct") or 0.0) >= 50.0
        ),
    }
    return {"passed": all(checks.values()), "checks": checks}


def maybe_open_sealed_test(
    policy_metrics: Mapping[str, Any],
    loader: Callable[[], dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    gate = evidence_gate(policy_metrics)
    if not gate["passed"]:
        return (
            "RESEARCH_HOLD",
            {
                "status": "SEALED_UNLOADED",
                "json_parsed": False,
                "reason": "one-session policy validation gate failed",
            },
        )
    return (
        "FROZEN_PENDING_PROSPECTIVE",
        {
            "status": "OPENED_ONCE_AFTER_VALIDATION_PASS",
            "json_parsed": True,
            **loader(),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--num-boost-round", type=int, default=800)
    parser.add_argument("--early-stopping-rounds", type=int, default=60)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError("model output directory must be new")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "complete"
        or manifest.get("clone_model_id")
        != "contextual_options_next_session_close_v1"
        or manifest.get("target_horizon_sessions") != 1
        or manifest.get("round_trip_cost_pct") != 0.25
        or manifest.get("panel_sha256") != file_sha256(args.input)
    ):
        raise ValueError("invalid contextual one-session panel manifest")

    structure = scan_panel_structure(args.input)
    splits = split_dates(structure)
    training_rows = read_rows_for_dates(
        args.input, splits["technical_train"]
    )
    fit_rows = read_rows_for_dates(
        args.input, splits["technical_fit_validation"]
    )
    training_rows = [
        row for row in training_rows if row.get(TARGET) is not None
    ]
    fit_rows = [row for row in fit_rows if row.get(TARGET) is not None]
    names = technical_feature_names(training_rows)
    x_train = matrix(training_rows, names)
    x_fit = matrix(fit_rows, names)
    y_train = np.asarray(
        [float(row[TARGET]) > 0.0 for row in training_rows], dtype=np.int32
    )
    y_fit = np.asarray(
        [float(row[TARGET]) > 0.0 for row in fit_rows], dtype=np.int32
    )
    train_set = lgb.Dataset(
        x_train, label=y_train, feature_name=names, free_raw_data=True
    )
    fit_set = lgb.Dataset(
        x_fit,
        label=y_fit,
        reference=train_set,
        feature_name=names,
        free_raw_data=True,
    )
    model = lgb.train(
        {
            "objective": "binary",
            "metric": ["binary_logloss", "auc"],
            "learning_rate": 0.025,
            "num_leaves": 31,
            "min_data_in_leaf": 100,
            "feature_fraction": 0.85,
            "lambda_l1": 2.0,
            "lambda_l2": 8.0,
            "verbosity": -1,
            "seed": 42,
            "force_col_wise": True,
            "num_threads": -1,
        },
        train_set,
        num_boost_round=args.num_boost_round,
        valid_sets=[fit_set],
        valid_names=["fit_validation"],
        callbacks=[
            lgb.early_stopping(args.early_stopping_rounds, verbose=False),
            lgb.log_evaluation(0),
        ],
    )

    policy_rows = read_rows_for_dates(
        args.input, splits["policy_validation"]
    )
    policy_scores = model.predict(
        matrix(policy_rows, names), num_iteration=model.best_iteration
    )
    policy_picks, policy_daily = choose_daily_candidates(
        policy_rows, policy_scores
    )
    policy_metrics = selection_metrics(policy_picks)
    policy_gate = evidence_gate(policy_metrics)

    def load_test() -> dict[str, Any]:
        test_rows = read_rows_for_dates(args.input, splits["sealed_test"])
        test_scores = model.predict(
            matrix(test_rows, names), num_iteration=model.best_iteration
        )
        test_picks, test_daily = choose_daily_candidates(
            test_rows, test_scores
        )
        return {
            "metrics": selection_metrics(test_picks),
            "daily_audit": test_daily,
        }

    status, test = maybe_open_sealed_test(policy_metrics, load_test)
    args.output_dir.mkdir(parents=True)
    model_path = args.output_dir / "technical_context_classifier.txt"
    model.save_model(str(model_path), num_iteration=model.best_iteration)
    report = {
        "status": status,
        "research_only": True,
        "execution_enabled": False,
        "source_model_id": "contextual_options_top_quarter",
        "clone_model_id": "contextual_options_next_session_close_v1",
        "model_family": "technical context plus prior unusual call buying",
        "feature_contract": "technical_* only in classifier",
        "candidate_rule": (
            "complete >=400-symbol same-day option panel; technical score "
            "in daily top quarter; call volume z-score >=3 using >=10 prior "
            "snapshots; at most five highest-scoring candidates"
        ),
        "target": TARGET,
        "target_definition": (
            "next regular-session open to that session's official close, "
            "minus 0.25% round-trip cost"
        ),
        "feature_names": names,
        "best_iteration": int(model.best_iteration),
        "model_path": str(model_path),
        "model_sha256": file_sha256(model_path),
        "panel_path": str(args.input),
        "panel_sha256": file_sha256(args.input),
        "panel_manifest_path": str(args.manifest),
        "panel_manifest_sha256": file_sha256(args.manifest),
        "split": {
            name: {
                "dates": len(days),
                "first": days[0] if days else None,
                "last": days[-1] if days else None,
            }
            for name, days in splits.items()
        },
        "technical_fit": {
            "train_rows": len(training_rows),
            "fit_validation_rows": len(fit_rows),
            "train_positive_rate": round(float(np.mean(y_train)), 6),
            "fit_validation_positive_rate": round(
                float(np.mean(y_fit)), 6
            ),
        },
        "policy_validation": {
            **policy_metrics,
            "gate": policy_gate,
            "daily_audit": policy_daily,
        },
        "test": test,
        "warnings": [
            "retrospective fixed-membership research contains survivorship bias",
            "historical passage alone cannot authorize trading",
            "source-model evidence is not inherited by this clone",
            "no paper or live orders are enabled",
        ],
    }
    report_path = args.output_dir / "training_report.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": status,
                "policy_signals": policy_metrics["signals"],
                "policy_dates": policy_metrics["decision_dates"],
                "policy_mean_net_return_pct": policy_metrics[
                    "mean_net_return_pct"
                ],
                "policy_median_net_return_pct": policy_metrics[
                    "median_net_return_pct"
                ],
                "policy_win_rate_pct": policy_metrics["win_rate_pct"],
                "policy_pass": policy_gate["passed"],
                "test_status": test["status"],
                "output": str(report_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
