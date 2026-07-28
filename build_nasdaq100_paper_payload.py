from __future__ import annotations

"""Build a frozen Nasdaq-100 clone payload for paper-only observation."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np


POLICY_ID = "nasdaq100_technical_clone_v1"
LOCKED_SCORE_CUTOFF = 0.15986412677273237


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_symbols(path: Path) -> set[str]:
    return {
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def build_payload(
    rows: list[dict[str, Any]],
    model: lgb.Booster,
    symbols: set[str],
    *,
    cutoff: float = LOCKED_SCORE_CUTOFF,
    max_candidates: int = 5,
) -> dict[str, Any]:
    eligible = [row for row in rows if str(row.get("symbol") or "").upper() in symbols]
    dates = {str(row.get("market_date") or "") for row in eligible}
    if not eligible or len(dates) != 1 or "" in dates:
        raise ValueError("Nasdaq payload requires one complete, nonempty market date")
    matrix = np.asarray(
        [[float(row.get(name) or 0.0) for name in model.feature_name()] for row in eligible],
        dtype=np.float32,
    )
    scored = sorted(
        (
            {**row, "technical_context_score": float(score)}
            for row, score in zip(eligible, model.predict(matrix, num_iteration=model.best_iteration))
        ),
        key=lambda row: (-row["technical_context_score"], str(row["symbol"])),
    )
    ordered_scores = np.sort(np.asarray(
        [row["technical_context_score"] for row in scored], dtype=float,
    ))

    def confidence_rank(score: float) -> int:
        if len(ordered_scores) == 1:
            return 100
        below_or_equal = int(np.searchsorted(ordered_scores, score, side="right"))
        percentile = 1.0 + 99.0 * (below_or_equal - 1) / (len(ordered_scores) - 1)
        return max(1, min(100, int(round(percentile))))

    candidates = [
        {
            "symbol": str(row["symbol"]).upper(),
            "market_date": str(row["market_date"]),
            "technical_context_score": row["technical_context_score"],
            "locked_score_cutoff": cutoff,
            "confidence_rank_1_to_100": confidence_rank(row["technical_context_score"]),
            "confidence_rank_definition": "same-day trained-universe model-score percentile; not probability",
            "paper_decision": "BUY_CANDIDATE",
            "policy_id": POLICY_ID,
        }
        for row in scored
        if row["technical_context_score"] >= cutoff
    ][:max_candidates]
    return {
        "status": "paper_payload_ready",
        "research_only": True,
        "paper_only": True,
        "live_trading_enabled": False,
        "policy_id": POLICY_ID,
        "market_date": dates.pop(),
        "training_universe_size": len(symbols),
        "training_universe_symbols": sorted(symbols),
        "universe_rows": len(eligible),
        "locked_score_cutoff": cutoff,
        "max_candidates": max_candidates,
        "candidates": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--technical-panel", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-candidates", type=int, default=5)
    args = parser.parse_args()
    model = lgb.Booster(model_file=str(args.model))
    payload = build_payload(
        read_jsonl(args.technical_panel), model, read_symbols(args.symbols_file),
        max_candidates=args.max_candidates,
    )
    payload["input_artifacts"] = {
        "technical_panel_sha256": sha256(args.technical_panel),
        "symbols_file_sha256": sha256(args.symbols_file),
        "model_sha256": sha256(args.model),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"], "market_date": payload["market_date"],
        "universe_rows": payload["universe_rows"], "candidates": len(payload["candidates"]),
    }, indent=2))


if __name__ == "__main__":
    main()
