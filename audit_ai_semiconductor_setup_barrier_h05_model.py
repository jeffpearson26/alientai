from __future__ import annotations

"""Reproduce the terminal AI/semiconductor H05 model gates and artifact hashes."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb

from alientai_v2.research.ai_semiconductor_setup_barrier_h05 import ENGINE_NAMES
from train_ai_semiconductor_setup_barrier_h05_lgbm import (
    active,
    evaluate,
    read_jsonl,
    research_director,
    score_rows,
    select_candidates,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_CONTRACT = ROOT / "AI_SEMICONDUCTOR_SETUP_BARRIER_H05_LGBM_CONTRACT_20260825.json"
DEFAULT_PANEL_AUDIT = ROOT / "AI_SEMICONDUCTOR_SETUP_BARRIER_H05_PANEL_AUDIT_20260825.json"
DEFAULT_OUTPUT = ROOT / "AI_SEMICONDUCTOR_SETUP_BARRIER_H05_MODEL_AUDIT_20260825.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def audit(
    contract_path: Path = DEFAULT_CONTRACT,
    panel_audit_path: Path = DEFAULT_PANEL_AUDIT,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    panel_audit = json.loads(panel_audit_path.read_text(encoding="utf-8"))
    panel_root = resolve(str(contract["panel_output_root"]))
    model_root = resolve(str(contract["model_output_root"]))
    panel_summary = json.loads((panel_root / "summary.json").read_text(encoding="utf-8"))
    report_path = model_root / "training_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if panel_audit.get("status") != "PASS":
        errors.append("panel audit is not PASS")
    if report.get("contract_sha256") != sha256(contract_path):
        errors.append("contract hash mismatch")
    if report.get("panel_audit_sha256") != sha256(panel_audit_path):
        errors.append("panel audit hash mismatch")
    for flag in ("execution_enabled", "paper_trading_enabled", "orders_created", "provider_contacted", "prospective_outcomes_read", "hyperparameter_search_performed", "sealed_test_retrained_after_open"):
        if bool(report.get(flag)):
            errors.append(f"unsafe report flag: {flag}")
    if report.get("authorization") != "NONE_RESEARCH_ONLY":
        errors.append("authorization mismatch")
    for name, expected in report.get("artifacts", {}).items():
        path = model_root / name
        if not path.exists() or sha256(path) != expected:
            errors.append(f"artifact hash mismatch: {name}")
    policy_all = read_jsonl(Path(panel_summary["partition_artifacts"]["POLICY_VALIDATION"]["path"]))
    recomputed_policy: dict[str, Any] = {}
    policy_selections: dict[str, list[dict[str, Any]]] = {}
    passing: list[str] = []
    for engine in ENGINE_NAMES:
        engine_report = report["engines"][engine]
        engine_root = model_root / engine.lower()
        model = lgb.Booster(model_file=str(engine_root / "target_first_classifier.txt"))
        calibrator = json.loads((engine_root / "isotonic_calibrator.json").read_text(encoding="utf-8"))
        rows = active(policy_all, engine)
        scored = score_rows(rows, model, calibrator, float(engine_report["mean_non_target_net_return_pct"]), contract, engine)
        selections = select_candidates(scored, contract)
        evaluation = evaluate(rows, scored, selections, float(engine_report["calibration_base_rate"]), contract)
        recomputed_policy[engine] = evaluation
        policy_selections[engine] = selections
        if evaluation["all_gates_pass"]:
            passing.append(engine)
        recorded = engine_report["policy_validation"]
        if evaluation["gate_checks"] != recorded["gate_checks"]:
            errors.append(f"policy gate reproduction mismatch: {engine}")
        if evaluation["metrics"]["candidates"] != recorded["metrics"]["candidates"]:
            errors.append(f"policy selection count mismatch: {engine}")
        preserved = read_jsonl(engine_root / "policy_validation_selections.jsonl")
        if [(row["market_date"], row["symbol"]) for row in preserved] != [(row["market_date"], row["symbol"]) for row in selections]:
            errors.append(f"policy selection artifact mismatch: {engine}")
    if passing != report.get("policy_passing_engines"):
        errors.append("passing-engine identity mismatch")
    sealed_opened = bool(report.get("sealed_test_opened"))
    if sealed_opened != bool(passing):
        errors.append("sealed-test opening rule mismatch")
    sealed_recomputed: dict[str, Any] | None = None
    if not sealed_opened:
        for engine in ENGINE_NAMES:
            if report["engines"][engine].get("sealed_test") is not None:
                errors.append(f"sealed result present after failed policy: {engine}")
            if (model_root / engine.lower() / "sealed_test_selections.jsonl").exists():
                errors.append(f"sealed artifact present after failed policy: {engine}")
    else:
        sealed_all = read_jsonl(Path(panel_summary["partition_artifacts"]["SEALED_TEST"]["path"]))
        selections_by_engine: dict[str, list[dict[str, Any]]] = {}
        sealed_recomputed = {}
        for engine in passing:
            engine_report = report["engines"][engine]
            engine_root = model_root / engine.lower()
            model = lgb.Booster(model_file=str(engine_root / "target_first_classifier.txt"))
            calibrator = json.loads((engine_root / "isotonic_calibrator.json").read_text(encoding="utf-8"))
            rows = active(sealed_all, engine)
            scored = score_rows(rows, model, calibrator, float(engine_report["mean_non_target_net_return_pct"]), contract, engine)
            selections = select_candidates(scored, contract)
            evaluation = evaluate(rows, scored, selections, float(engine_report["calibration_base_rate"]), contract)
            sealed_recomputed[engine] = evaluation
            selections_by_engine[engine] = selections
            if evaluation["gate_checks"] != engine_report["sealed_test"]["gate_checks"]:
                errors.append(f"sealed gate reproduction mismatch: {engine}")
        director = research_director(selections_by_engine)
        preserved = read_jsonl(model_root / "research_director_sealed_selections.jsonl")
        if [(row["market_date"], row["symbol"], row["engine"]) for row in preserved] != [(row["market_date"], row["symbol"], row["engine"]) for row in director]:
            errors.append("research-director sealed selection mismatch")
    expected_status = (
        "SEALED_TEST_PASS_RESEARCH_ONLY"
        if passing and all(report["engines"][engine]["sealed_test"]["all_gates_pass"] for engine in passing)
        else "SEALED_TEST_COMPLETE_RESEARCH_HOLD"
        if passing
        else "RESEARCH_HOLD_POLICY_VALIDATION_FAILED"
    )
    if report.get("status") != expected_status:
        errors.append("terminal status mismatch")
    return {
        "schema_version": 1,
        "status": "PASS" if not errors else "FAIL",
        "research_only": True,
        "execution_enabled": False,
        "orders_created": False,
        "contract_id": contract["contract_id"],
        "contract_sha256": sha256(contract_path),
        "panel_audit_sha256": sha256(panel_audit_path),
        "training_report_sha256": sha256(report_path),
        "terminal_disposition": report.get("status"),
        "policy_passing_engines": passing,
        "sealed_test_opened": sealed_opened,
        "recomputed_policy_validation": recomputed_policy,
        "recomputed_sealed_test": sealed_recomputed,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--panel-audit", type=Path, default=DEFAULT_PANEL_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = audit(args.contract, args.panel_audit)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "terminal_disposition": report["terminal_disposition"],
        "policy_passing_engines": report["policy_passing_engines"],
        "sealed_test_opened": report["sealed_test_opened"],
        "errors": report["errors"],
    }, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
