from __future__ import annotations

"""Train, calibrate, gate, and conditionally open the sealed AI/semi H05 test."""

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.research.ai_semiconductor_setup_barrier_h05 import (
    ENGINE_NAMES,
    FEATURE_NAMES,
    apply_isotonic,
    fit_isotonic,
    load_rows,
    probability_metrics,
    trade_metrics,
)


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "AI_SEMICONDUCTOR_SETUP_BARRIER_H05_LGBM_CONTRACT_20260825.json"
PANEL_AUDIT = ROOT / "AI_SEMICONDUCTOR_SETUP_BARRIER_H05_PANEL_AUDIT_20260825.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")


def matrix(rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    return np.asarray([[float(row[name]) for name in FEATURE_NAMES] for row in rows], dtype=np.float64)


def labels(rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    return np.asarray([int(row["target_first_label"]) for row in rows], dtype=np.float64)


def active(rows: Sequence[dict[str, Any]], engine: str) -> list[dict[str, Any]]:
    field = f"setup_{engine.lower()}"
    return [row for row in rows if int(row[field]) == 1]


def model_params(contract: Mapping[str, Any]) -> dict[str, Any]:
    frozen = contract["training_design"]["fixed_hyperparameters"]
    return {
        "objective": "binary",
        "metric": "binary_logloss",
        "learning_rate": float(frozen["learning_rate"]),
        "num_leaves": int(frozen["num_leaves"]),
        "max_depth": int(frozen["max_depth"]),
        "min_data_in_leaf": int(frozen["min_data_in_leaf"]),
        "feature_fraction": float(frozen["feature_fraction"]),
        "bagging_fraction": float(frozen["bagging_fraction"]),
        "bagging_freq": int(frozen["bagging_freq"]),
        "lambda_l1": float(frozen["lambda_l1"]),
        "lambda_l2": float(frozen["lambda_l2"]),
        "verbosity": -1,
        "seed": int(frozen["seed"]),
        "feature_fraction_seed": int(frozen["seed"]),
        "bagging_seed": int(frozen["seed"]),
        "data_random_seed": int(frozen["seed"]),
        "deterministic": True,
        "force_col_wise": True,
        "num_threads": 4,
    }


def train_final_model(
    train_rows: Sequence[dict[str, Any]],
    valid_rows: Sequence[dict[str, Any]],
    contract: Mapping[str, Any],
) -> lgb.Booster:
    if len(set(labels(train_rows))) != 2 or len(set(labels(valid_rows))) != 2:
        raise ValueError("train and fit-validation rows must each contain both classes")
    frozen = contract["training_design"]["fixed_hyperparameters"]
    return lgb.train(
        model_params(contract),
        lgb.Dataset(matrix(train_rows), label=labels(train_rows), feature_name=FEATURE_NAMES, free_raw_data=False),
        num_boost_round=int(frozen["num_boost_round"]),
        valid_sets=[lgb.Dataset(matrix(valid_rows), label=labels(valid_rows), feature_name=FEATURE_NAMES, free_raw_data=False)],
        valid_names=["FIT_VALIDATION"],
        callbacks=[lgb.early_stopping(int(frozen["early_stopping_rounds"]), verbose=False), lgb.log_evaluation(0)],
    )


def action_for_probability(probability: float, contract: Mapping[str, Any]) -> str:
    for item in contract["probability_actions"]:
        if float(item["minimum"]) <= probability < float(item["maximum_exclusive"]):
            return str(item["action"])
    raise ValueError("calibrated probability is outside frozen action bands")


def score_rows(
    rows: Sequence[dict[str, Any]],
    model: lgb.Booster,
    calibrator: Mapping[str, Any],
    mean_non_target_net_return_pct: float,
    contract: Mapping[str, Any],
    engine: str,
) -> list[dict[str, Any]]:
    if not rows:
        return []
    raw = np.asarray(model.predict(matrix(rows), num_iteration=model.best_iteration), dtype=float)
    calibrated = apply_isotonic(raw, calibrator)
    target_net = float(contract["decision_and_exit"]["profit_target_pct_from_entry"]) - float(contract["decision_and_exit"]["round_trip_cost_pct"])
    scored = []
    for index, row in enumerate(rows):
        probability = float(calibrated[index])
        expected = probability * target_net + (1.0 - probability) * mean_non_target_net_return_pct
        scored.append({
            **row,
            "engine": engine,
            "raw_target_first_probability": float(raw[index]),
            "calibrated_target_first_probability": probability,
            "expected_net_return_pct": float(expected),
            "probability_action": action_for_probability(probability, contract),
        })
    return scored


def select_candidates(scored: Sequence[dict[str, Any]], contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    policy = contract["frozen_policy"]
    eligible = [
        row for row in scored
        if float(row["calibrated_target_first_probability"]) >= float(policy["minimum_calibrated_target_first_probability"])
        and float(row["expected_net_return_pct"]) > float(policy["minimum_expected_net_return_pct"])
    ]
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        by_date[str(row["market_date"])].append(row)
    selected = []
    for market_date in sorted(by_date):
        ordered = sorted(
            by_date[market_date],
            key=lambda row: (-float(row["expected_net_return_pct"]), -float(row["calibrated_target_first_probability"]), str(row["symbol"])),
        )
        selected.extend(ordered[: int(policy["maximum_candidates_per_engine_per_decision_date"])])
    return selected


def reliability_table(rows: Sequence[dict[str, Any]], contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    output = []
    for band in contract["probability_actions"]:
        selected = [
            row for row in rows
            if float(band["minimum"]) <= float(row["calibrated_target_first_probability"]) < float(band["maximum_exclusive"])
        ]
        output.append({
            "minimum_probability": band["minimum"],
            "maximum_exclusive_probability": band["maximum_exclusive"],
            "action": band["action"],
            "rows": len(selected),
            "mean_predicted_probability": mean(float(row["calibrated_target_first_probability"]) for row in selected) if selected else None,
            "actual_target_first_rate": mean(int(row["target_first_label"]) for row in selected) if selected else None,
            "mean_net_return_pct": mean(float(row["net_return_pct"]) for row in selected) if selected else None,
        })
    return output


def grouped_candidate_metrics(rows: Sequence[dict[str, Any]], key_name: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if key_name == "symbol":
            key = str(row["symbol"])
        elif key_name == "regime":
            sector = "SOXX_POSITIVE_20D" if float(row["soxx_return_20d_pct"]) > 0 else "SOXX_NONPOSITIVE_20D"
            volatility = "VOL_PROXY_CALMING" if float(row["vixy_proxy_return_5d_pct"]) <= 0 else "VOL_PROXY_RISING"
            key = f"{sector}__{volatility}"
        else:
            raise ValueError(key_name)
        grouped[key].append(row)
    return {
        key: {
            "trades": len(values),
            "mean_net_return_pct": mean(float(row["net_return_pct"]) for row in values),
            "target_first_rate_pct": mean(int(row["target_first_label"]) for row in values) * 100.0,
        }
        for key, values in sorted(grouped.items())
    }


def matched_controls(rows: Sequence[dict[str, Any]], contract: Mapping[str, Any]) -> dict[str, Any]:
    if not rows:
        return {"rows": 0, "qqq_mean_net_return_pct": None, "soxx_mean_net_return_pct": None}
    source = resolve(str(contract["source_archive"]))
    result: dict[str, list[float]] = {"QQQ": [], "SOXX": []}
    cost = float(contract["decision_and_exit"]["round_trip_cost_pct"])
    for symbol in result:
        candles = load_rows(source / f"{symbol}_daily.json")
        by_date = {str(row["date"]): row for row in candles}
        for row in rows:
            entry = by_date.get(str(row["entry_market_date"]))
            exit_row = by_date.get(str(row["exit_market_date"]))
            if not entry or not exit_row:
                continue
            result[symbol].append((float(exit_row["close"]) / float(entry["open"]) - 1.0) * 100.0 - cost)
    return {
        "rows": len(rows),
        "qqq_mean_net_return_pct": mean(result["QQQ"]) if result["QQQ"] else None,
        "soxx_mean_net_return_pct": mean(result["SOXX"]) if result["SOXX"] else None,
    }


def evaluate(
    all_rows: Sequence[dict[str, Any]],
    scored: Sequence[dict[str, Any]],
    candidates: Sequence[dict[str, Any]],
    calibration_base_rate: float,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    probabilities = np.asarray([float(row["calibrated_target_first_probability"]) for row in scored], dtype=float)
    actual = labels(scored)
    metrics = trade_metrics(
        candidates,
        all_rows,
        account=float(contract["frozen_policy"]["simulated_account_usd_per_engine"]),
        notional=float(contract["frozen_policy"]["fixed_comparison_notional_usd"]),
    )
    metrics["probability"] = probability_metrics(actual, probabilities, calibration_base_rate)
    metrics["reliability_table"] = reliability_table(scored, contract)
    metrics["by_symbol"] = grouped_candidate_metrics(candidates, "symbol")
    metrics["by_regime"] = grouped_candidate_metrics(candidates, "regime")
    metrics["matched_controls"] = matched_controls(candidates, contract)
    gates = contract["policy_validation_gates"]
    checks = {
        "minimum_candidates": metrics["candidates"] >= int(gates["minimum_candidates"]),
        "minimum_candidate_dates": metrics["candidate_dates"] >= int(gates["minimum_candidate_dates"]),
        "minimum_mean_net_return_pct": metrics["mean_net_return_pct"] is not None and metrics["mean_net_return_pct"] > float(gates["minimum_mean_net_return_pct"]),
        "minimum_median_net_return_pct": metrics["median_net_return_pct"] is not None and metrics["median_net_return_pct"] > float(gates["minimum_median_net_return_pct"]),
        "minimum_target_first_rate_pct": metrics["target_first_rate_pct"] is not None and metrics["target_first_rate_pct"] >= float(gates["minimum_target_first_rate_pct"]),
        "minimum_profit_factor": metrics["profit_factor"] >= float(gates["minimum_profit_factor"]),
        "maximum_drawdown_pct": metrics["maximum_drawdown_pct"] >= float(gates["maximum_drawdown_pct"]),
        "minimum_brier_skill_pct": metrics["probability"]["brier_skill_pct"] > float(gates["minimum_brier_skill_pct"]),
        "maximum_ece_10bin": metrics["probability"]["ece_10bin"] <= float(gates["maximum_ece_10bin"]),
    }
    return {"metrics": metrics, "gate_checks": checks, "all_gates_pass": all(checks.values())}


def walk_forward(engine: str, all_development_rows: Sequence[dict[str, Any]], contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    output = []
    rounds = int(contract["training_design"]["walk_forward_diagnostic_num_boost_round"])
    for fold in contract["walk_forward_diagnostics"]:
        train_rows = active([row for row in all_development_rows if str(row["market_date"]) <= str(fold["train_through"])], engine)
        evaluation_rows = active([
            row for row in all_development_rows
            if str(fold["evaluate_first"]) <= str(row["market_date"]) <= str(fold["evaluate_last"])
        ], engine)
        record: dict[str, Any] = {**fold, "train_rows": len(train_rows), "evaluation_rows": len(evaluation_rows)}
        if len(train_rows) < 100 or len(evaluation_rows) < 10 or len(set(labels(train_rows))) != 2 or len(set(labels(evaluation_rows))) != 2:
            record["status"] = "INSUFFICIENT_ROWS_OR_CLASSES"
            output.append(record)
            continue
        booster = lgb.train(
            model_params(contract),
            lgb.Dataset(matrix(train_rows), label=labels(train_rows), feature_name=FEATURE_NAMES),
            num_boost_round=rounds,
            callbacks=[lgb.log_evaluation(0)],
        )
        raw = np.asarray(booster.predict(matrix(evaluation_rows)), dtype=float)
        actual = labels(evaluation_rows)
        baseline = float(np.mean(labels(train_rows)))
        record.update({
            "status": "COMPLETE",
            "raw_probability_metrics": probability_metrics(actual, raw, baseline),
            "actual_target_first_rate": float(np.mean(actual)),
            "mean_raw_probability": float(np.mean(raw)),
        })
        output.append(record)
    return output


def research_director(selections_by_engine: Mapping[str, Sequence[dict[str, Any]]]) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for engine, rows in selections_by_engine.items():
        for row in rows:
            by_date[str(row["market_date"])].append({**row, "engine": engine})
    selected = []
    for market_date in sorted(by_date):
        selected.append(sorted(
            by_date[market_date],
            key=lambda row: (-float(row["expected_net_return_pct"]), -float(row["calibrated_target_first_probability"]), str(row["engine"]), str(row["symbol"])),
        )[0])
    return selected


def main() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    panel_audit = json.loads(PANEL_AUDIT.read_text(encoding="utf-8"))
    if panel_audit.get("status") != "PASS" or panel_audit.get("contract_sha256") != sha256(CONTRACT):
        raise ValueError("panel audit is not a current PASS")
    panel_root = resolve(str(contract["panel_output_root"]))
    panel_summary = json.loads((panel_root / "summary.json").read_text(encoding="utf-8"))
    model_root = resolve(str(contract["model_output_root"]))
    if model_root.exists() and any(model_root.iterdir()):
        raise ValueError(f"model output root must be new or empty: {model_root}")
    model_root.mkdir(parents=True, exist_ok=True)
    partitions = {
        name: read_jsonl(Path(panel_summary["partition_artifacts"][name]["path"]))
        for name in ("TRAIN", "FIT_VALIDATION", "CALIBRATION", "POLICY_VALIDATION")
    }
    development_rows = partitions["TRAIN"] + partitions["FIT_VALIDATION"]
    engine_reports: dict[str, Any] = {}
    models: dict[str, lgb.Booster] = {}
    calibrators: dict[str, dict[str, Any]] = {}
    non_target_means: dict[str, float] = {}
    policy_selections: dict[str, list[dict[str, Any]]] = {}
    artifacts: dict[str, str] = {}
    for engine in ENGINE_NAMES:
        engine_root = model_root / engine.lower()
        engine_root.mkdir(parents=True, exist_ok=False)
        train_rows = active(partitions["TRAIN"], engine)
        valid_rows = active(partitions["FIT_VALIDATION"], engine)
        calibration_rows = active(partitions["CALIBRATION"], engine)
        policy_rows = active(partitions["POLICY_VALIDATION"], engine)
        if min(len(train_rows), len(valid_rows), len(calibration_rows), len(policy_rows)) == 0:
            raise ValueError(f"empty required setup partition: {engine}")
        model = train_final_model(train_rows, valid_rows, contract)
        raw_calibration = np.asarray(model.predict(matrix(calibration_rows), num_iteration=model.best_iteration), dtype=float)
        calibration_labels = labels(calibration_rows)
        if len(set(calibration_labels)) != 2:
            raise ValueError(f"calibration lacks both classes: {engine}")
        calibrator = fit_isotonic(raw_calibration, calibration_labels)
        non_targets = [float(row["net_return_pct"]) for row in calibration_rows if int(row["target_first_label"]) == 0]
        if not non_targets:
            raise ValueError(f"calibration lacks non-target outcomes: {engine}")
        mean_non_target = mean(non_targets)
        scored_policy = score_rows(policy_rows, model, calibrator, mean_non_target, contract, engine)
        selected_policy = select_candidates(scored_policy, contract)
        evaluation = evaluate(policy_rows, scored_policy, selected_policy, float(np.mean(calibration_labels)), contract)
        model_path = engine_root / "target_first_classifier.txt"
        calibrator_path = engine_root / "isotonic_calibrator.json"
        selection_path = engine_root / "policy_validation_selections.jsonl"
        model.save_model(str(model_path), num_iteration=model.best_iteration)
        calibrator_path.write_text(json.dumps(calibrator, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_jsonl(selection_path, selected_policy)
        for path in (model_path, calibrator_path, selection_path):
            artifacts[str(path.relative_to(model_root)).replace("\\", "/")] = sha256(path)
        engine_reports[engine] = {
            "status": "POLICY_VALIDATION_PASS" if evaluation["all_gates_pass"] else "RESEARCH_HOLD_POLICY_VALIDATION_FAILED",
            "setup_partition_rows": {
                "TRAIN": len(train_rows),
                "FIT_VALIDATION": len(valid_rows),
                "CALIBRATION": len(calibration_rows),
                "POLICY_VALIDATION": len(policy_rows),
            },
            "best_iteration": int(model.best_iteration),
            "calibration_base_rate": float(np.mean(calibration_labels)),
            "mean_non_target_net_return_pct": mean_non_target,
            "walk_forward_diagnostics": walk_forward(engine, development_rows, contract),
            "policy_validation": evaluation,
            "sealed_test_status": "ELIGIBLE_TO_OPEN" if evaluation["all_gates_pass"] else "SEALED_UNLOADED",
            "sealed_test": None,
        }
        models[engine] = model
        calibrators[engine] = calibrator
        non_target_means[engine] = mean_non_target
        policy_selections[engine] = selected_policy
    passing = [engine for engine in ENGINE_NAMES if engine_reports[engine]["policy_validation"]["all_gates_pass"]]
    director_policy = research_director({engine: policy_selections[engine] for engine in passing})
    director_policy_metrics = trade_metrics(
        director_policy,
        partitions["POLICY_VALIDATION"],
        account=10000.0,
        notional=float(contract["frozen_policy"]["fixed_comparison_notional_usd"]),
    )
    sealed_test_opened = bool(passing)
    director_sealed: list[dict[str, Any]] = []
    if sealed_test_opened:
        sealed_rows = read_jsonl(Path(panel_summary["partition_artifacts"]["SEALED_TEST"]["path"]))
        sealed_by_engine: dict[str, list[dict[str, Any]]] = {}
        for engine in passing:
            rows = active(sealed_rows, engine)
            scored = score_rows(rows, models[engine], calibrators[engine], non_target_means[engine], contract, engine)
            selections = select_candidates(scored, contract)
            evaluation = evaluate(rows, scored, selections, engine_reports[engine]["calibration_base_rate"], contract)
            engine_reports[engine]["sealed_test_status"] = "OPENED_ONCE"
            engine_reports[engine]["sealed_test"] = evaluation
            path = model_root / engine.lower() / "sealed_test_selections.jsonl"
            write_jsonl(path, selections)
            artifacts[str(path.relative_to(model_root)).replace("\\", "/")] = sha256(path)
            sealed_by_engine[engine] = selections
        director_sealed = research_director(sealed_by_engine)
        path = model_root / "research_director_sealed_selections.jsonl"
        write_jsonl(path, director_sealed)
        artifacts[str(path.relative_to(model_root)).replace("\\", "/")] = sha256(path)
    all_sealed_pass = bool(passing) and all(engine_reports[engine]["sealed_test"]["all_gates_pass"] for engine in passing)
    status = (
        "SEALED_TEST_PASS_RESEARCH_ONLY" if all_sealed_pass
        else "SEALED_TEST_COMPLETE_RESEARCH_HOLD" if passing
        else "RESEARCH_HOLD_POLICY_VALIDATION_FAILED"
    )
    report = {
        "schema_version": 1,
        "status": status,
        "authorization": "NONE_RESEARCH_ONLY",
        "research_only": True,
        "execution_enabled": False,
        "paper_trading_enabled": False,
        "orders_created": False,
        "provider_contacted": False,
        "prospective_outcomes_read": False,
        "hyperparameter_search_performed": False,
        "sealed_test_opened": sealed_test_opened,
        "sealed_test_retrained_after_open": False,
        "contract_id": contract["contract_id"],
        "contract_sha256": sha256(CONTRACT),
        "panel_audit_sha256": sha256(PANEL_AUDIT),
        "panel_summary_sha256": sha256(panel_root / "summary.json"),
        "features": FEATURE_NAMES,
        "engines": engine_reports,
        "policy_passing_engines": passing,
        "research_director": {
            "trained_combiner": False,
            "policy_validation_selections": len(director_policy),
            "policy_validation_metrics": director_policy_metrics,
            "sealed_test_selections": len(director_sealed) if sealed_test_opened else None,
            "sealed_test_metrics": trade_metrics(director_sealed, sealed_rows, account=10000.0, notional=1000.0) if sealed_test_opened else None,
        },
        "volatility_context": contract["volatility_context"],
        "artifacts": artifacts,
    }
    report_path = model_root / "training_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": status,
        "policy_passing_engines": passing,
        "sealed_test_opened": sealed_test_opened,
        "engines": {
            engine: {
                "status": engine_reports[engine]["status"],
                "policy_candidates": engine_reports[engine]["policy_validation"]["metrics"]["candidates"],
                "policy_mean_net_return_pct": engine_reports[engine]["policy_validation"]["metrics"]["mean_net_return_pct"],
                "policy_profit_factor": engine_reports[engine]["policy_validation"]["metrics"]["profit_factor"],
            }
            for engine in ENGINE_NAMES
        },
    }, indent=2))


if __name__ == "__main__":
    main()
