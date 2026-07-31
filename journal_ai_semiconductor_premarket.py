from __future__ import annotations

"""Append-only prospective journal for the frozen AI/semiconductor premarket model."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import lightgbm as lgb
import numpy as np


MODEL_ID = "ai_semiconductor_technical_premarket_5d_20260731"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def merge_features(
    technical_rows: Iterable[Mapping[str, Any]],
    premarket_rows: Iterable[Mapping[str, Any]],
    market_date: str,
) -> list[dict[str, Any]]:
    technical = {(str(row["symbol"]).upper(), str(row["market_date"])): row for row in technical_rows}
    premarket = {(str(row["symbol"]).upper(), str(row["market_date"])): row for row in premarket_rows}
    if set(technical) != set(premarket):
        raise ValueError("technical and premarket keys must match exactly")
    if any(day != market_date for _, day in technical):
        raise ValueError("all rows must match the requested market date")
    output = []
    for key in sorted(technical):
        pm = premarket[key]
        if pm.get("premarket_available") is not True:
            raise ValueError(f"premarket unavailable for {key[0]}|{key[1]}")
        output.append({
            **technical[key],
            **{f"model_{name}": value for name, value in pm.items() if name.startswith("premarket_")},
        })
    return output


def rank_candidates(rows: list[dict[str, Any]], scores: np.ndarray, maximum_candidates: int) -> list[dict[str, Any]]:
    if maximum_candidates < 1:
        raise ValueError("maximum_candidates must be positive")
    ranked = sorted(
        ({**row, "model_score": float(score)} for row, score in zip(rows, scores)),
        key=lambda row: (-row["model_score"], row["symbol"]),
    )
    return ranked[:maximum_candidates]


def append_unique(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    existing = {
        (row.get("model_id"), row.get("market_date"), row.get("symbol"))
        for row in read_jsonl(path)
    } if path.exists() else set()
    additions = [
        dict(row) for row in rows
        if (row.get("model_id"), row.get("market_date"), row.get("symbol")) not in existing
    ]
    if additions:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            for row in additions:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    return len(additions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--technical", type=Path, required=True)
    parser.add_argument("--premarket", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--market-date", required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--maximum-candidates", type=int, default=2)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    requested_manifest = {
        "status": "frozen",
        "research_only": True,
        "execution_enabled": False,
        "model_id": MODEL_ID,
        "target_horizon_sessions": 5,
        "decision_time": "after completed regular-session close",
        "entry_reference": "next-session open",
        "exit_reference": "fifth subsequent session close",
        "round_trip_cost_pct": 0.25,
        "selection_policy": "top two scores in frozen 17-symbol universe",
        "score_is_probability": False,
        "model_sha256": file_sha256(args.model),
        "training_report_sha256": file_sha256(args.report),
        "symbols_file_sha256": file_sha256(args.symbols_file),
        "maximum_candidates": args.maximum_candidates,
    }
    if args.manifest.exists():
        if json.loads(args.manifest.read_text(encoding="utf-8")) != requested_manifest:
            raise ValueError("existing frozen manifest does not match requested configuration")
    else:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(requested_manifest, indent=2) + "\n", encoding="utf-8")

    rows = merge_features(read_jsonl(args.technical), read_jsonl(args.premarket), args.market_date)
    names = report["feature_names"]
    values = np.asarray(
        [[float(row.get(name) or 0.0) for name in names] for row in rows],
        dtype=np.float32,
    )
    model = lgb.Booster(model_file=str(args.model))
    selected = rank_candidates(rows, model.predict(values, num_iteration=model.best_iteration), args.maximum_candidates)
    now = datetime.now(timezone.utc).isoformat()
    observations = [{
        "model_id": MODEL_ID,
        "model_sha256": requested_manifest["model_sha256"],
        "market_date": row["market_date"],
        "symbol": row["symbol"],
        "decision_close": row.get("close"),
        "model_score": row["model_score"],
        "score_is_probability": False,
        "rank": rank,
        "target_horizon_sessions": 5,
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
        "eligible_universe": len(rows),
        "selected": len(observations),
        "appended": added,
        "symbols": [row["symbol"] for row in observations],
        "journal": str(args.journal),
    }, indent=2))


if __name__ == "__main__":
    main()
