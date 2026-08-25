from __future__ import annotations

"""Compile the frozen source-pure AI/semiconductor setup-barrier H05 panel."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

from alientai_v2.research.ai_semiconductor_setup_barrier_h05 import (
    ENGINE_NAMES,
    FEATURE_NAMES,
    build_feature_values,
    detect_setups,
    load_rows,
    resolve_path_label,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_CONTRACT = ROOT / "AI_SEMICONDUCTOR_SETUP_BARRIER_H05_LGBM_CONTRACT_20260825.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def partition_for_date(market_date: str, partitions: Sequence[Mapping[str, Any]]) -> str:
    matches = [
        str(item["name"])
        for item in partitions
        if str(item["first_date"]) <= market_date <= str(item["last_date"])
    ]
    if len(matches) != 1:
        raise ValueError(f"decision date has {len(matches)} partition matches: {market_date}")
    return matches[0]


def build_panel(contract: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = resolve(str(contract["source_archive"]))
    universe = resolve(str(contract["universe_file"]))
    source_audit_path = resolve(str(contract["source_subset_audit"]))
    source_audit = json.loads(source_audit_path.read_text(encoding="utf-8"))
    if source_audit.get("status") != "PASS" or source_audit.get("contract_sha256") != sha256(DEFAULT_CONTRACT):
        raise ValueError("exact source subset audit is not a current PASS")
    if sha256(source / "manifest.json") != str(contract["source_archive_manifest_sha256"]):
        raise ValueError("source manifest hash mismatch")
    if sha256(universe) != str(contract["universe_sha256"]):
        raise ValueError("universe hash mismatch")
    symbols = [line.strip() for line in universe.read_text(encoding="utf-8").splitlines() if line.strip()]
    if symbols != list(contract["candidate_symbols"]):
        raise ValueError("candidate identity or order mismatch")
    all_symbols = symbols + list(contract["context_symbols"])
    candles = {symbol: load_rows(source / f"{symbol}_daily.json") for symbol in all_symbols}
    by_date = {
        symbol: {str(row["date"]): index for index, row in enumerate(rows)}
        for symbol, rows in candles.items()
    }
    qqq_dates = [str(row["date"]) for row in candles["QQQ"]]
    qqq_position = {value: index for index, value in enumerate(qqq_dates)}
    for partition in contract["chronological_partitions"]:
        count = sum(str(partition["first_date"]) <= value <= str(partition["last_date"]) for value in qqq_dates)
        if count != int(partition["expected_context_dates"]):
            raise ValueError(f"context date count mismatch: {partition['name']}")
    first_date = str(contract["historical_window"]["start_date"])
    last_date = str(contract["historical_window"]["last_decision_date"])
    minimum_breadth = int(contract["feature_contract"]["minimum_usable_breadth_symbols"])
    breadth_by_date: dict[str, dict[str, float]] = {}
    for market_date in qqq_dates:
        if not first_date <= market_date <= last_date:
            continue
        green: list[float] = []
        above: list[float] = []
        returns: list[float] = []
        for symbol in symbols:
            index = by_date[symbol].get(market_date)
            if index is None or index < 20:
                continue
            rows = candles[symbol]
            current = float(rows[index]["close"])
            prior = float(rows[index - 1]["close"])
            average20 = sum(float(row["close"]) for row in rows[index - 19 : index + 1]) / 20.0
            green.append(float(current > prior))
            above.append(float(current > average20))
            returns.append((current / prior - 1.0) * 100.0)
        if len(green) >= minimum_breadth:
            breadth_by_date[market_date] = {
                "usable_symbols": float(len(green)),
                "green_fraction": sum(green) / len(green),
                "above_20dma_fraction": sum(above) / len(above),
                "median_return_1d_pct": median(returns),
            }
    output: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    partition_rows: Counter[str] = Counter()
    partition_dates: dict[str, set[str]] = {str(item["name"]): set() for item in contract["chronological_partitions"]}
    setup_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    exit_contract = contract["decision_and_exit"]
    for symbol in symbols:
        built = 0
        symbol_dates: list[str] = []
        rows = candles[symbol]
        for market_date in qqq_dates:
            if not first_date <= market_date <= last_date:
                continue
            if market_date not in breadth_by_date:
                skipped["breadth_unavailable"] += 1
                continue
            qindex = qqq_position[market_date]
            if qindex + int(exit_contract["horizon_sessions"]) >= len(qqq_dates):
                skipped["future_context_unavailable"] += 1
                continue
            index = by_date[symbol].get(market_date)
            if index is None or index < 60:
                skipped["stock_lookback_unavailable"] += 1
                continue
            path_dates = qqq_dates[qindex + 1 : qindex + 6]
            path_indices = [by_date[symbol].get(value) for value in path_dates]
            if any(value is None for value in path_indices):
                skipped["complete_five_session_path_unavailable"] += 1
                continue
            context_histories: dict[str, Sequence[Mapping[str, Any]]] = {}
            context_ok = True
            for context_symbol in contract["context_symbols"]:
                context_index = by_date[context_symbol].get(market_date)
                if context_index is None or context_index < 60:
                    context_ok = False
                    break
                context_histories[context_symbol] = candles[context_symbol][: context_index + 1]
            if not context_ok:
                skipped["context_lookback_unavailable"] += 1
                continue
            features = build_feature_values(rows[: index + 1], context_histories, breadth_by_date[market_date])
            setups = detect_setups(features)
            path_rows = [rows[int(value)] for value in path_indices]
            label = resolve_path_label(
                path_rows,
                entry_open=float(path_rows[0]["open"]),
                target_pct=float(exit_contract["profit_target_pct_from_entry"]),
                stop_pct=float(exit_contract["protective_stop_pct_from_entry"]),
                cost_pct=float(exit_contract["round_trip_cost_pct"]),
            )
            partition = partition_for_date(market_date, contract["chronological_partitions"])
            result = {
                "market_date": market_date,
                "symbol": symbol,
                "partition": partition,
                **features,
                **{f"setup_{name.lower()}": int(setups[name]) for name in ENGINE_NAMES},
                "setup_count": int(sum(setups.values())),
                **label,
                "provider": contract["provider"],
                "source_endpoint": contract["source_endpoint"],
                "volatility_context_symbol": "VIXY",
                "volatility_context_is_proxy": True,
            }
            output.append(result)
            built += 1
            symbol_dates.append(market_date)
            partition_rows[partition] += 1
            partition_dates[partition].add(market_date)
            outcome_counts[label["path_outcome"]] += 1
            for engine, active in setups.items():
                if active:
                    setup_counts[engine] += 1
        coverage.append({
            "symbol": symbol,
            "rows": built,
            "first_date": symbol_dates[0] if symbol_dates else None,
            "last_date": symbol_dates[-1] if symbol_dates else None,
        })
    output.sort(key=lambda row: (row["market_date"], row["symbol"]))
    source_artifacts = {
        symbol: {"path": str(source / f"{symbol}_daily.json"), "sha256": sha256(source / f"{symbol}_daily.json")}
        for symbol in all_symbols
    }
    summary = {
        "schema_version": 1,
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "paper_trading_enabled": False,
        "provider_contacted": False,
        "prospective_outcomes_read": False,
        "sealed_test_predictions_read": False,
        "orders_created": False,
        "contract_id": contract["contract_id"],
        "contract_sha256": sha256(DEFAULT_CONTRACT),
        "source_subset_audit_sha256": sha256(source_audit_path),
        "source_manifest_sha256": sha256(source / "manifest.json"),
        "universe_sha256": sha256(universe),
        "feature_names": FEATURE_NAMES,
        "feature_count": len(FEATURE_NAMES),
        "rows": len(output),
        "symbols": len(symbols),
        "coverage": coverage,
        "setup_counts": dict(setup_counts),
        "outcome_counts": dict(outcome_counts),
        "partition_rows": dict(partition_rows),
        "partition_dates": {name: len(values) for name, values in partition_dates.items()},
        "skipped": dict(skipped),
        "source_artifacts": source_artifacts,
    }
    return output, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    if args.contract.resolve() != DEFAULT_CONTRACT.resolve():
        raise ValueError("this frozen compiler accepts only its exact contract")
    output_root = resolve(str(contract["panel_output_root"]))
    if output_root.exists() and any(output_root.iterdir()):
        raise ValueError(f"panel output root must be new or empty: {output_root}")
    rows, summary = build_panel(contract)
    output_root.mkdir(parents=True, exist_ok=True)
    rows_path = output_root / "rows.jsonl"
    with rows_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    artifacts: dict[str, dict[str, Any]] = {}
    for partition in contract["chronological_partitions"]:
        name = str(partition["name"])
        path = output_root / f"{name.lower()}.jsonl"
        selected = [row for row in rows if row["partition"] == name]
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in selected:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
        artifacts[name] = {"path": str(path), "rows": len(selected), "sha256": sha256(path)}
    summary.update({
        "rows_path": str(rows_path),
        "rows_sha256": sha256(rows_path),
        "partition_artifacts": artifacts,
    })
    summary_path = output_root / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("status", "rows", "symbols", "setup_counts", "outcome_counts", "partition_rows")}, indent=2))


if __name__ == "__main__":
    main()
