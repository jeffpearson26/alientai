from __future__ import annotations

"""Append-only, non-executing prospective score-basket journal for Nasdaq models."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from evaluate_context_portfolio import file_sha256
from evaluate_score_percentile_baskets import DEFAULT_PERCENTILE_EDGES, percentile_edges
from journal_nasdaq_challengers import (
    latest_common_date,
    load_candles,
    prospective_row,
    schwab_session_date,
    symbols,
    validate_market_date_freshness,
)
from alientai_v2.research.score_calibration import percentile_rank


CONFIGURATIONS = (
    {
        "model_id": "nasdaq100_complete_101_baseline_v1",
        "model_path": "nasdaq100_complete_clone/model_10pct/natural_technical_context_classifier.txt",
        "report_path": "nasdaq100_complete_clone/model_10pct/natural_technical_context_report.json",
        "qqq_relative": False,
    },
    {
        "model_id": "nasdaq100_complete_101_qqq_relative_v1",
        "model_path": "nasdaq100_relative_qqq/model_10pct/natural_technical_context_classifier.txt",
        "report_path": "nasdaq100_relative_qqq/model_10pct/natural_technical_context_report.json",
        "qqq_relative": True,
    },
)


def frozen_manifest(research_root: Path, percentile_edges_list: Sequence[int]) -> dict[str, Any]:
    models = []
    for config in CONFIGURATIONS:
        model = research_root / config["model_path"]
        report = research_root / config["report_path"]
        models.append({
            "model_id": config["model_id"],
            "model_sha256": file_sha256(model),
            "training_report_sha256": file_sha256(report),
            "qqq_relative": config["qqq_relative"],
        })
    return {
        "status": "frozen",
        "research_only": True,
        "execution_enabled": False,
        "target_horizon_sessions": 5,
        "percentile_edges": list(percentile_edges_list),
        "selection_contract": "Record every complete-universe score; never select a score basket from outcomes.",
        "models": models,
    }


def basket_for_score(score: float, cutoffs: Mapping[int, float], edges: Sequence[int]) -> str:
    for lower, upper in zip(edges, edges[1:]):
        upper_inclusive = upper == edges[-1]
        if score >= cutoffs[lower] and (score < cutoffs[upper] or (upper_inclusive and score <= cutoffs[upper])):
            return f"{lower}-{upper}"
    raise ValueError("score does not fit frozen percentile boundaries")


def append_unique(path: Path, rows: Sequence[Mapping[str, Any]]) -> int:
    existing = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                existing.add((row.get("model_id"), row.get("market_date"), row.get("symbol")))
    additions = [
        row for row in rows
        if (row["model_id"], row["market_date"], row["symbol"]) not in existing
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in additions:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")
    return len(additions)


def build_observations(
    daily_dir: Path,
    symbol_list: Sequence[str],
    research_root: Path,
    market_date: str,
    edges: Sequence[int],
) -> list[dict[str, Any]]:
    benchmark = load_candles(daily_dir / "QQQ_schwab_1d_max.csv")
    observations = []
    for config in CONFIGURATIONS:
        model_path = research_root / config["model_path"]
        report_path = research_root / config["report_path"]
        report = json.loads(report_path.read_text(encoding="utf-8"))
        rows = []
        for symbol in symbol_list:
            rows.append(prospective_row(
                load_candles(daily_dir / f"{symbol}_schwab_1d_max.csv"),
                symbol,
                market_date,
                benchmark if config["qqq_relative"] else None,
                "QQQ" if config["qqq_relative"] else None,
            ))
        features = report["feature_names"]
        model = lgb.Booster(model_file=str(model_path))
        scores = [float(value) for value in model.predict(np.asarray([
            [float(row.get(name) or 0.0) for name in features] for row in rows
        ], dtype=np.float32), num_iteration=model.best_iteration)]
        validation_rows = [
            json.loads(line) for line in Path(report["input"]).read_text(encoding="utf-8").splitlines()
            if line.strip() and report["split"]["validation_start"] <= json.loads(line)["market_date"] <= report["split"]["validation_end"]
        ]
        validation_matrix = np.asarray([
            [float(row.get(name) or 0.0) for name in features] for row in validation_rows
        ], dtype=np.float32)
        validation_scores = model.predict(validation_matrix, num_iteration=model.best_iteration)
        cutoffs = percentile_edges([float(value) for value in validation_scores], edges)
        for row, score in zip(rows, scores):
            observations.append({
                **row,
                "model_id": config["model_id"],
                "model_sha256": file_sha256(model_path),
                "market_session_date": schwab_session_date(market_date),
                "score_percentile_basket": basket_for_score(score, cutoffs, edges),
                "confidence_rank_1_to_100": percentile_rank(score, scores),
                "confidence_rank_definition": "same-day universe score percentile; not probability",
                "model_score": score,
                "target_horizon_sessions": 5,
                "status": "pending",
                "research_only": True,
                "execution_decision": "AVOID",
                "journaled_at_utc": datetime.now(timezone.utc).isoformat(),
            })
    return observations


def main() -> None:
    parser = argparse.ArgumentParser(description="Append a full-universe, non-executing Nasdaq score basket observation.")
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--market-date")
    parser.add_argument("--maximum-market-age-calendar-days", type=int, default=1)
    parser.add_argument("--percentile-edges", type=int, nargs="+", default=DEFAULT_PERCENTILE_EDGES)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    symbol_list = symbols(args.symbols_file)
    market_date = args.market_date or latest_common_date(args.daily_dir, symbol_list, "QQQ")
    session_date = schwab_session_date(market_date)
    age = validate_market_date_freshness(session_date, datetime.now(timezone.utc).date(), args.maximum_market_age_calendar_days)
    manifest = frozen_manifest(args.research_root, args.percentile_edges)
    if args.manifest.exists():
        if json.loads(args.manifest.read_text(encoding="utf-8")) != manifest:
            raise ValueError("existing frozen manifest does not match requested configuration")
    observations = build_observations(args.daily_dir, symbol_list, args.research_root, market_date, args.percentile_edges)
    if args.dry_run:
        appended = 0
    else:
        if not args.manifest.exists():
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        appended = append_unique(args.journal, observations)
    print(json.dumps({
        "status": "dry_run" if args.dry_run else "complete",
        "research_only": True,
        "execution_enabled": False,
        "market_date": market_date,
        "market_session_date": session_date,
        "market_date_age_calendar_days": age,
        "eligible_universe": len(symbol_list),
        "observations_scored": len(observations),
        "observations_appended": appended,
        "basket_counts": {key: sum(row["score_percentile_basket"] == key for row in observations) for key in sorted({row["score_percentile_basket"] for row in observations})},
    }, indent=2))


if __name__ == "__main__":
    main()
