from __future__ import annotations

"""Append-only prospective journal for six frozen AI/semiconductor intraday models."""

import argparse
import hashlib
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np


MODEL_CONFIGS = (
    ("20m_technical", 20, 0.20, "ai_semiconductor_20min_technical"),
    ("20m_premarket", 20, 0.10, "ai_semiconductor_20min_premarket"),
    ("20m_calls", 20, 0.10, "ai_semiconductor_20min_calls"),
    ("60m_technical", 60, 0.50, "ai_semiconductor_60min_technical"),
    ("60m_premarket", 60, 0.10, "ai_semiconductor_60min_premarket"),
    ("60m_calls", 60, 0.10, "ai_semiconductor_60min_calls"),
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def by_symbol(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    output: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "").upper()
        if not symbol or symbol in output:
            raise ValueError(f"invalid or duplicate symbol: {symbol}")
        output[symbol] = row
    return output


def merge_inputs(
    technical_rows: Sequence[Mapping[str, Any]],
    premarket_rows: Sequence[Mapping[str, Any]],
    call_rows: Sequence[Mapping[str, Any]],
    decision_date: str,
) -> list[dict[str, Any]]:
    technical, premarket, calls = by_symbol(technical_rows), by_symbol(premarket_rows), by_symbol(call_rows)
    if set(technical) != set(premarket) or set(technical) != set(calls):
        raise ValueError("technical, premarket, and call symbols must match exactly")
    decision = date.fromisoformat(decision_date)
    output = []
    for symbol in sorted(technical):
        tech, pm, call = technical[symbol], premarket[symbol], calls[symbol]
        prior_dates = {str(tech.get("market_date") or ""), str(call.get("market_date") or "")}
        if len(prior_dates) != 1 or date.fromisoformat(next(iter(prior_dates))) >= decision:
            raise ValueError(f"technical/call rows must share a prior market date for {symbol}")
        if str(pm.get("market_date") or "") != decision_date or pm.get("premarket_available") is not True:
            raise ValueError(f"current 09:25 premarket row unavailable for {symbol}")
        output.append({
            **tech,
            **{f"model_{name}": value for name, value in pm.items() if name.startswith("premarket_")},
            **{f"model_{name}": value for name, value in call.items() if name.startswith("call_")},
            "symbol": symbol,
            "market_date": decision_date,
            "prior_feature_market_date": next(iter(prior_dates)),
        })
    return output


def append_unique(path: Path, observations: Sequence[Mapping[str, Any]]) -> int:
    existing = {
        (row["model_id"], row["market_date"], row["symbol"])
        for row in read_jsonl(path)
    } if path.exists() else set()
    additions = [
        row for row in observations
        if (row["model_id"], row["market_date"], row["symbol"]) not in existing
    ]
    if additions:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            for row in additions:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    return len(additions)


def score_models(rows: list[dict[str, Any]], model_root: Path, decision_date: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    observations, manifests = [], []
    now = datetime.now(timezone.utc).isoformat()
    for short_name, horizon, fraction, directory_name in MODEL_CONFIGS:
        directory = model_root / directory_name
        model_path = directory / "natural_technical_context_classifier.txt"
        report_path = directory / "natural_technical_context_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        names = report["feature_names"]
        values = np.asarray(
            [[float(row.get(name) or 0.0) for name in names] for row in rows],
            dtype=np.float32,
        )
        model = lgb.Booster(model_file=str(model_path))
        scores = model.predict(values, num_iteration=model.best_iteration)
        count = max(1, math.ceil(len(rows) * fraction))
        ranked = sorted(
            ({**row, "model_score": float(score)} for row, score in zip(rows, scores)),
            key=lambda row: (-row["model_score"], row["symbol"]),
        )[:count]
        model_id = f"ai_semiconductor_{short_name}_frozen_20260731"
        model_hash = sha256(model_path)
        manifests.append({
            "model_id": model_id,
            "horizon_minutes": horizon,
            "daily_fraction": fraction,
            "daily_candidate_count": count,
            "model_sha256": model_hash,
            "training_report_sha256": sha256(report_path),
        })
        for rank, row in enumerate(ranked, 1):
            observations.append({
                "model_id": model_id,
                "model_sha256": model_hash,
                "market_date": decision_date,
                "prior_feature_market_date": row["prior_feature_market_date"],
                "symbol": row["symbol"],
                "rank": rank,
                "model_score": row["model_score"],
                "score_is_probability": False,
                "horizon_minutes": horizon,
                "entry_reference": "09:30 ET bar open",
                "exit_reference": f"{9 + ((30 + horizon) // 60):02d}:{(30 + horizon) % 60:02d} ET",
                "round_trip_cost_pct": 0.25,
                "status": "pending",
                "journaled_at_utc": now,
                "research_only": True,
                "execution_decision": "AVOID",
            })
    return observations, manifests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--technical", type=Path, required=True)
    parser.add_argument("--premarket", type=Path, required=True)
    parser.add_argument("--call-history", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    rows = merge_inputs(
        read_jsonl(args.technical), read_jsonl(args.premarket),
        read_jsonl(args.call_history), args.decision_date,
    )
    observations, models = score_models(rows, args.model_root, args.decision_date)
    requested_manifest = {
        "status": "frozen",
        "research_only": True,
        "execution_enabled": False,
        "universe_size": len(rows),
        "decision_time": "09:25 ET after premarket cutoff",
        "entry_reference": "09:30 ET bar open",
        "models": models,
    }
    if args.manifest.exists():
        if json.loads(args.manifest.read_text(encoding="utf-8")) != requested_manifest:
            raise ValueError("frozen manifest mismatch")
    else:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(requested_manifest, indent=2) + "\n", encoding="utf-8")
    additions = append_unique(args.journal, observations)
    print(json.dumps({
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "decision_date": args.decision_date,
        "models": len(models),
        "observations": len(observations),
        "appended": additions,
        "journal": str(args.journal),
    }, indent=2))


if __name__ == "__main__":
    main()
