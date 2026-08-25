from __future__ import annotations

"""Independently audit the frozen AI/semiconductor setup-barrier H05 panel."""

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from alientai_v2.research.ai_semiconductor_setup_barrier_h05 import (
    ENGINE_NAMES,
    FEATURE_NAMES,
    detect_setups,
    load_rows,
    resolve_path_label,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_CONTRACT = ROOT / "AI_SEMICONDUCTOR_SETUP_BARRIER_H05_LGBM_CONTRACT_20260825.json"
DEFAULT_SOURCE_AUDIT = ROOT / "AI_SEMICONDUCTOR_SETUP_BARRIER_H05_SOURCE_AUDIT_20260825.json"
DEFAULT_OUTPUT = ROOT / "AI_SEMICONDUCTOR_SETUP_BARRIER_H05_PANEL_AUDIT_20260825.json"


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
    source_audit_path: Path = DEFAULT_SOURCE_AUDIT,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    panel_root = resolve(str(contract["panel_output_root"]))
    summary_path = panel_root / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    source_audit = json.loads(source_audit_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if source_audit.get("status") != "PASS":
        errors.append("source audit is not PASS")
    if summary.get("contract_sha256") != sha256(contract_path):
        errors.append("contract hash mismatch")
    if summary.get("source_subset_audit_sha256") != sha256(source_audit_path):
        errors.append("source audit hash mismatch")
    for flag in ("execution_enabled", "paper_trading_enabled", "provider_contacted", "prospective_outcomes_read", "sealed_test_predictions_read", "orders_created"):
        if bool(summary.get(flag)):
            errors.append(f"unsafe summary flag: {flag}")
    if summary.get("feature_names") != FEATURE_NAMES or int(summary.get("feature_count", -1)) != len(FEATURE_NAMES):
        errors.append("feature identity mismatch")
    if len(FEATURE_NAMES) != int(contract["feature_contract"]["feature_count"]):
        errors.append("contract feature count mismatch")
    source = resolve(str(contract["source_archive"]))
    symbols = list(contract["candidate_symbols"])
    candles = {symbol: load_rows(source / f"{symbol}_daily.json") for symbol in symbols + ["QQQ"]}
    by_date = {symbol: {str(row["date"]): row for row in rows} for symbol, rows in candles.items()}
    qqq_dates = [str(row["date"]) for row in candles["QQQ"]]
    qqq_position = {value: index for index, value in enumerate(qqq_dates)}
    partition_counts: Counter[str] = Counter()
    partition_dates: dict[str, set[str]] = defaultdict(set)
    symbol_counts: Counter[str] = Counter()
    setup_counts: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    inspected = 0
    exit_contract = contract["decision_and_exit"]
    for partition in contract["chronological_partitions"]:
        name = str(partition["name"])
        artifact = summary.get("partition_artifacts", {}).get(name)
        if not artifact:
            errors.append(f"missing partition artifact: {name}")
            continue
        path = Path(str(artifact["path"]))
        if sha256(path) != str(artifact["sha256"]):
            errors.append(f"partition hash mismatch: {name}")
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                inspected += 1
                partition_counts[name] += 1
                partition_dates[name].add(str(row["market_date"]))
                symbol_counts[str(row["symbol"])] += 1
                outcomes[str(row["path_outcome"])] += 1
                if row.get("partition") != name or not str(partition["first_date"]) <= str(row["market_date"]) <= str(partition["last_date"]):
                    errors.append(f"partition violation: {row.get('symbol')} {row.get('market_date')}")
                if row.get("volatility_context_symbol") != "VIXY" or row.get("volatility_context_is_proxy") is not True:
                    errors.append("volatility proxy disclosure is missing")
                if any(field not in row or not math.isfinite(float(row[field])) for field in FEATURE_NAMES):
                    errors.append(f"missing or non-finite feature: {row.get('symbol')} {row.get('market_date')}")
                recomputed_setups = detect_setups(row)
                for engine in ENGINE_NAMES:
                    expected = int(recomputed_setups[engine])
                    actual = int(row.get(f"setup_{engine.lower()}", -1))
                    if expected != actual:
                        errors.append(f"setup mismatch: {engine} {row.get('symbol')} {row.get('market_date')}")
                    if actual:
                        setup_counts[engine] += 1
                if int(row.get("setup_count", -1)) != sum(recomputed_setups.values()):
                    errors.append(f"setup count mismatch: {row.get('symbol')} {row.get('market_date')}")
                symbol = str(row["symbol"])
                market_date = str(row["market_date"])
                qindex = qqq_position.get(market_date)
                if qindex is None:
                    errors.append(f"decision date absent from QQQ calendar: {market_date}")
                    continue
                path_dates = qqq_dates[qindex + 1 : qindex + 6]
                if len(path_dates) != 5 or any(value not in by_date[symbol] for value in path_dates):
                    errors.append(f"source path missing during audit: {symbol} {market_date}")
                    continue
                path_rows = [by_date[symbol][value] for value in path_dates]
                reconstructed = resolve_path_label(
                    path_rows,
                    entry_open=float(path_rows[0]["open"]),
                    target_pct=float(exit_contract["profit_target_pct_from_entry"]),
                    stop_pct=float(exit_contract["protective_stop_pct_from_entry"]),
                    cost_pct=float(exit_contract["round_trip_cost_pct"]),
                )
                for field in ("entry_market_date", "exit_market_date", "path_outcome", "target_first_label", "sessions_to_exit"):
                    if reconstructed[field] != row.get(field):
                        errors.append(f"path field mismatch: {field} {symbol} {market_date}")
                for field in ("entry_adjusted_open", "exit_adjusted_price", "gross_return_pct", "net_return_pct", "maximum_favorable_excursion_pct", "maximum_adverse_excursion_pct"):
                    if abs(float(reconstructed[field]) - float(row.get(field))) > 1e-9:
                        errors.append(f"path numeric mismatch: {field} {symbol} {market_date}")
                if len(errors) >= 40:
                    break
        if partition_counts[name] != int(artifact["rows"]):
            errors.append(f"partition row-count mismatch: {name}")
        if len(errors) >= 40:
            break
    if inspected != int(summary.get("rows", -1)):
        errors.append("total row-count mismatch")
    if set(symbol_counts) != set(symbols):
        errors.append("candidate symbol coverage mismatch")
    if dict(setup_counts) != summary.get("setup_counts"):
        errors.append("setup total mismatch")
    if dict(outcomes) != summary.get("outcome_counts"):
        errors.append("outcome total mismatch")
    report = {
        "schema_version": 1,
        "status": "PASS" if not errors else "FAIL",
        "research_only": True,
        "execution_enabled": False,
        "orders_created": False,
        "contract_id": contract["contract_id"],
        "contract_sha256": sha256(contract_path),
        "source_audit_sha256": sha256(source_audit_path),
        "panel_summary_sha256": sha256(summary_path),
        "rows_inspected": inspected,
        "symbols": len(symbol_counts),
        "partition_rows": dict(partition_counts),
        "partition_dates": {key: len(value) for key, value in partition_dates.items()},
        "setup_counts": dict(setup_counts),
        "outcome_counts": dict(outcomes),
        "same_session_dual_barrier_behavior": "STOP_FIRST_CONSERVATIVE",
        "errors": errors,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--source-audit", type=Path, default=DEFAULT_SOURCE_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = audit(args.contract, args.source_audit)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
