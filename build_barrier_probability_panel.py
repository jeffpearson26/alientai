from __future__ import annotations

"""Build a source-pure, stage-sharded barrier-probability panel."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from alientai_v2.research.barrier_probability_model import (
    FEATURE_LOOKBACK,
    FEATURE_NAMES,
    adjusted_daily_candles,
    chronological_date_sets,
    resolve_barrier,
    technical_features,
)


STAGES = (
    "train",
    "fit_validation",
    "calibration",
    "policy_validation",
    "sealed_test",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_symbols(path: Path) -> list[str]:
    symbols = [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not symbols or len(symbols) != len(set(symbols)):
        raise ValueError("universe symbols must be nonempty and unique")
    return symbols


def json_lines(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def symbol_filename(symbol: str) -> str:
    return f"{symbol.replace('/', '-').replace('.', '-')}_daily.json"


def source_map(
    config: dict[str, Any],
    symbols: list[str],
) -> dict[str, tuple[Path, str]]:
    mapping: dict[str, tuple[Path, str]] = {}
    aliases = {
        str(key).upper(): str(value).upper()
        for key, value in (config.get("source_symbol_aliases") or {}).items()
    }
    if not set(aliases).issubset(symbols):
        raise ValueError("source symbol aliases must only name universe symbols")
    for route in config["source_routes"]:
        root = Path(route["root"])
        route_symbols = (
            symbols
            if route.get("all_universe_symbols") is True
            else route["symbols"]
        )
        for symbol in route_symbols:
            symbol = str(symbol).upper()
            if symbol in mapping:
                raise ValueError(f"duplicate source route for {symbol}")
            mapping[symbol] = (
                root / symbol_filename(symbol),
                aliases.get(symbol, symbol),
            )
    if set(mapping) != set(symbols):
        missing = sorted(set(symbols) - set(mapping))
        extra = sorted(set(mapping) - set(symbols))
        raise ValueError(f"source routing mismatch; missing={missing}; extra={extra}")
    return mapping


def file_record(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    manifest = path.parent / "manifest.json"
    return {
        "path": str(path.resolve()),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "source_manifest_path": (
            str(manifest.resolve()) if manifest.is_file() else None
        ),
        "source_manifest_sha256": (
            sha256(manifest) if manifest.is_file() else None
        ),
    }


def build_rows(
    *,
    model_id: str,
    symbol: str,
    candles: list[dict[str, Any]],
    start_date: str,
    upper_pct: float,
    lower_pct: float,
    horizon: int,
) -> tuple[list[dict[str, Any]], Counter[str]]:
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for decision_index in range(FEATURE_LOOKBACK - 1, len(candles) - 1):
        decision_date = str(candles[decision_index]["market_date"])
        if decision_date < start_date:
            continue
        label = resolve_barrier(
            candles,
            decision_index,
            upper_pct=upper_pct,
            lower_pct=lower_pct,
            horizon_sessions=horizon,
        )
        counts[str(label["outcome_status"])] += 1
        if label.get("label_lower_bound") is None:
            continue
        try:
            features = technical_features(
                candles[
                    decision_index + 1 - FEATURE_LOOKBACK : decision_index + 1
                ]
            )
        except ValueError:
            counts["feature_unavailable"] += 1
            continue
        row = {
            "schema_version": 1,
            "model_id": model_id,
            "research_only": True,
            "execution_decision": "AVOID",
            "provider": "Alpha Vantage",
            "symbol": symbol,
            "market_date": decision_date,
            "decision_adjusted_close": float(
                candles[decision_index]["close"]
            ),
            "upper_barrier_pct": upper_pct * 100.0,
            "lower_barrier_pct": lower_pct * 100.0,
            "maximum_horizon_sessions": horizon,
            **features,
            **label,
        }
        rows.append(row)
    return rows, counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError("output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    config = json.loads(args.config.read_text(encoding="utf-8"))
    if not config.get("research_only") or config.get("execution_enabled"):
        raise ValueError("config must remain research-only")
    aliases = {
        str(key).upper(): str(value).upper()
        for key, value in (config.get("source_symbol_aliases") or {}).items()
    }
    universe_path = Path(config["universe_file"])
    symbols = read_symbols(universe_path)
    routes = source_map(config, symbols)
    upper_pct = float(config["upper_barrier_pct"]) / 100.0
    lower_pct = float(config["lower_barrier_pct"]) / 100.0
    horizon = int(config["maximum_horizon_sessions"])
    embargo = int(config["embargo_sessions_each_side"])

    temporary = args.output_dir / ".all_complete_rows.tmp.jsonl"
    source_records: dict[str, dict[str, Any]] = {}
    symbol_stats: dict[str, dict[str, Any]] = {}
    complete_dates: set[str] = set()
    outcome_counts: Counter[str] = Counter()
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for symbol in symbols:
            path, expected_source_symbol = routes[symbol]
            source_records[symbol] = file_record(path)
            candles = adjusted_daily_candles(path, expected_source_symbol)
            rows, counts = build_rows(
                model_id=str(config["model_id"]),
                symbol=symbol,
                candles=candles,
                start_date=str(config["start_date"]),
                upper_pct=upper_pct,
                lower_pct=lower_pct,
                horizon=horizon,
            )
            outcome_counts.update(counts)
            complete_dates.update(str(row["market_date"]) for row in rows)
            symbol_stats[symbol] = {
                "source_rows": len(candles),
                "source_first_date": candles[0]["market_date"],
                "source_latest_date": candles[-1]["market_date"],
                "complete_panel_rows": len(rows),
                "outcomes": dict(sorted(counts.items())),
            }
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

    date_sets = chronological_date_sets(
        sorted(complete_dates),
        embargo_sessions=embargo,
    )
    date_to_stage = {
        market_date: stage
        for stage in STAGES
        for market_date in date_sets[stage]
    }
    stage_max_dates = {
        stage: max(date_sets[stage])
        for stage in STAGES
    }
    stage_paths = {
        stage: args.output_dir / f"{stage}.jsonl"
        for stage in STAGES
    }
    stage_handles = {
        stage: path.open("w", encoding="utf-8", newline="\n")
        for stage, path in stage_paths.items()
    }
    stage_rows: Counter[str] = Counter()
    stage_symbols: dict[str, set[str]] = {stage: set() for stage in STAGES}
    purged_label_overlap = 0
    embargo_rows = 0
    try:
        for row in json_lines(temporary):
            market_date = str(row["market_date"])
            stage = date_to_stage.get(market_date)
            if stage is None:
                embargo_rows += 1
                continue
            if (
                str(row["label_information_end_date"])
                > stage_max_dates[stage]
            ):
                purged_label_overlap += 1
                continue
            stage_handles[stage].write(
                json.dumps(row, sort_keys=True) + "\n"
            )
            stage_rows[stage] += 1
            stage_symbols[stage].add(str(row["symbol"]))
    finally:
        for handle in stage_handles.values():
            handle.close()
        temporary.unlink()

    partitions = {}
    for stage, path in stage_paths.items():
        dates = sorted(date_sets[stage])
        partitions[stage] = {
            "path": str(path.resolve()),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "rows": stage_rows[stage],
            "symbols": len(stage_symbols[stage]),
            "decision_dates": len(dates),
            "first_decision_date": dates[0],
            "last_decision_date": dates[-1],
            "label_information_must_end_by": stage_max_dates[stage],
        }

    manifest = {
        "status": "complete",
        "schema_version": 1,
        "research_only": True,
        "execution_enabled": False,
        "model_id": config["model_id"],
        "provider": config["provider"],
        "config_path": str(args.config.resolve()),
        "config_sha256": sha256(args.config),
        "universe_path": str(universe_path.resolve()),
        "universe_sha256": sha256(universe_path),
        "symbols": symbols,
        "symbol_count": len(symbols),
        "source_symbol_aliases": aliases,
        "feature_names": list(FEATURE_NAMES),
        "feature_lookback_sessions": FEATURE_LOOKBACK,
        "start_date": config["start_date"],
        "decision_time": config["decision_time"],
        "entry": config["entry"],
        "upper_barrier_pct": config["upper_barrier_pct"],
        "lower_barrier_pct": config["lower_barrier_pct"],
        "maximum_horizon_sessions": horizon,
        "same_session_double_touch_policy": (
            config["same_session_double_touch_policy"]
        ),
        "timeout_policy": config["timeout_policy"],
        "split_fractions": {
            "train": 0.50,
            "fit_validation": 0.15,
            "calibration": 0.10,
            "policy_validation": 0.10,
            "sealed_test": 0.15,
        },
        "embargo_sessions_each_side": embargo,
        "partition_contract": (
            "whole decision dates; rows additionally purged unless all label "
            "information ends inside the assigned stage"
        ),
        "partitions": partitions,
        "excluded": {
            "embargo_rows": embargo_rows,
            "label_overlap_rows": purged_label_overlap,
            "incomplete_outcomes": outcome_counts.get(
                "incomplete_unresolved", 0
            )
            + outcome_counts.get("incomplete_no_entry", 0),
        },
        "outcome_counts_before_partitioning": dict(
            sorted(outcome_counts.items())
        ),
        "symbol_stats": symbol_stats,
        "source_files": source_records,
        "sealed_test_contract": (
            "the panel builder and independent content auditor may materialize "
            "and verify labels; the model trainer must not load sealed_test.jsonl "
            "unless every frozen policy-validation gate passes"
        ),
        "warnings": [
            "fixed current universe has survivorship and selection bias",
            "daily bars cannot order same-session double barrier touches",
            "MS and NOW use shorter same-provider compact histories",
            "no historical result authorizes paper or live execution",
        ],
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "output": str(args.output_dir),
                "symbols": len(symbols),
                "decision_dates": len(complete_dates),
                "partition_rows": dict(stage_rows),
                "outcomes": dict(outcome_counts),
                "manifest": str(manifest_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
