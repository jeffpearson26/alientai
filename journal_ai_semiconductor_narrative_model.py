from __future__ import annotations

"""Freeze and prospectively journal a multi-horizon narrative model."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from typing import Any, Iterable, Mapping

import lightgbm as lgb
import numpy as np

from build_ai_semiconductor_earnings_context import attach_earnings, read_jsonl
from journal_ai_semiconductor_premarket import append_unique, merge_features, rank_candidates


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_entry(report: Mapping[str, Any], horizon: int, stage: str) -> Mapping[str, Any]:
    matches = [
        item for item in report.get("models") or []
        if int(item.get("horizon_sessions") or 0) == horizon and item.get("stage") == stage
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one report model for horizon={horizon}, stage={stage}")
    return matches[0]


def frozen_contract(
    report_path: Path,
    model_path: Path,
    symbols_path: Path,
    model_id: str,
    horizon: int,
    stage: str,
) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    entry = model_entry(report, horizon, stage)
    if sha256(model_path) != entry["model_sha256"]:
        raise ValueError("model hash does not match the training report")
    symbols = [
        line.strip().upper()
        for line in symbols_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    fraction = float(entry["validation_selected_fraction"])
    return {
        "status": "frozen",
        "research_only": True,
        "execution_enabled": False,
        "model_id": model_id,
        "horizon_sessions": horizon,
        "stage": stage,
        "universe_size": len(symbols),
        "selection_fraction": fraction,
        "maximum_candidates": max(1, ceil(len(symbols) * fraction)),
        "decision_time": "after completed regular-session close",
        "entry_reference": "next regular-session open",
        "exit_reference": f"{horizon} subsequent session close",
        "round_trip_cost_pct": 0.25,
        "model_sha256": sha256(model_path),
        "training_report_sha256": sha256(report_path),
        "symbols_file_sha256": sha256(symbols_path),
        "score_is_probability": False,
        "historical_test_reused": True,
        "promotion_status": "future_observation_only",
    }


def ensure_manifest(path: Path, requested: Mapping[str, Any]) -> None:
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != requested:
            raise ValueError("existing frozen manifest does not match requested contract")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(requested, indent=2) + "\n", encoding="utf-8")


def score_rows(
    rows: list[dict[str, Any]],
    model_path: Path,
    feature_names: list[str],
    maximum_candidates: int,
) -> list[dict[str, Any]]:
    values = np.asarray(
        [[float(row.get(name) or 0.0) for name in feature_names] for row in rows],
        dtype=np.float32,
    )
    model = lgb.Booster(model_file=str(model_path))
    scores = model.predict(values, num_iteration=model.best_iteration)
    return rank_candidates(rows, scores, maximum_candidates)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--horizon", type=int, required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--freeze-only", action="store_true")
    parser.add_argument("--technical", type=Path)
    parser.add_argument("--premarket", type=Path)
    parser.add_argument("--earnings", type=Path)
    parser.add_argument("--market-date")
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    entry = model_entry(report, args.horizon, args.stage)
    contract = frozen_contract(
        args.report, args.model, args.symbols_file, args.model_id, args.horizon, args.stage
    )
    ensure_manifest(args.manifest, contract)
    if args.freeze_only:
        print(json.dumps({"status": "frozen", "manifest": str(args.manifest), **contract}, indent=2))
        return
    required = (args.technical, args.premarket, args.earnings, args.market_date, args.journal)
    if any(value is None for value in required):
        raise ValueError("scoring requires technical, premarket, earnings, market-date, and journal")

    rows = merge_features(
        read_jsonl(args.technical), read_jsonl(args.premarket), args.market_date
    )
    rows = attach_earnings(rows, read_jsonl(args.earnings))
    if len(rows) != contract["universe_size"]:
        raise ValueError("prospective universe does not match frozen universe size")
    selected = score_rows(
        rows, args.model, list(entry["feature_names"]), contract["maximum_candidates"]
    )
    now = datetime.now(timezone.utc).isoformat()
    observations = [{
        "model_id": args.model_id,
        "model_sha256": contract["model_sha256"],
        "market_date": row["market_date"],
        "symbol": row["symbol"],
        "decision_close": row.get("close"),
        "model_score": row["model_score"],
        "score_is_probability": False,
        "rank": rank,
        "target_horizon_sessions": args.horizon,
        "status": "pending",
        "journaled_at_utc": now,
        "research_only": True,
        "execution_decision": "AVOID",
    } for rank, row in enumerate(selected, 1)]
    added = append_unique(args.journal, observations)
    print(json.dumps({
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "market_date": args.market_date,
        "selected": len(observations),
        "appended": added,
        "symbols": [row["symbol"] for row in observations],
    }, indent=2))


if __name__ == "__main__":
    main()
