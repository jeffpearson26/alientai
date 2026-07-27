from __future__ import annotations

"""Score a complete future panel with the frozen two-day shadow policy."""

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import lightgbm as lgb
import numpy as np

from train_selective_five_day_challenger import matrix, read_jsonl


def select_shadow_candidates(
    rows: Sequence[dict[str, Any]],
    scores: Sequence[float],
    *,
    score_cutoff: float,
    expected_universe_size: int,
    minimum_coverage_fraction: float,
) -> dict[str, Any]:
    if len(rows) != len(scores):
        raise ValueError("rows and scores must have equal length")
    if expected_universe_size < 1:
        raise ValueError("expected_universe_size must be positive")
    dates = {str(row.get("market_date") or "") for row in rows}
    if len(dates) != 1 or "" in dates:
        raise ValueError("shadow input must contain exactly one market date")
    symbols = [str(row.get("symbol") or "").upper().strip() for row in rows]
    if any(not symbol for symbol in symbols) or len(set(symbols)) != len(symbols):
        raise ValueError("shadow input requires unique nonblank symbols")
    coverage = len(rows) / expected_universe_size
    if coverage < minimum_coverage_fraction:
        return {
            "status": "INCOMPLETE_UNIVERSE_HOLD",
            "market_date": next(iter(dates)),
            "coverage_fraction": coverage,
            "candidates": [],
            "execution_enabled": False,
        }
    ranked = sorted(
        zip(rows, [float(score) for score in scores]),
        key=lambda item: item[1],
        reverse=True,
    )
    candidates = [
        {
            "symbol": str(row["symbol"]).upper().strip(),
            "market_date": str(row["market_date"]),
            "large_move_score": score,
            "rank": rank,
            "decision": "SHADOW_OBSERVE_ONLY",
        }
        for rank, (row, score) in enumerate(ranked, start=1)
        if score >= score_cutoff
    ]
    return {
        "status": "SHADOW_SCORED",
        "market_date": next(iter(dates)),
        "coverage_fraction": coverage,
        "score_cutoff": score_cutoff,
        "candidates": candidates,
        "execution_enabled": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("data_v2/rcef_research/selective_two_day_shadow_policy.json"),
    )
    parser.add_argument("--expected-universe-size", type=int, default=483)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    policy = json.loads((root / args.policy).read_text(encoding="utf-8"))
    if policy.get("status") != "FROZEN_FOR_FUTURE_SHADOW_ONLY":
        raise ValueError("a frozen future-shadow policy is required")
    if policy.get("execution_enabled") is not False:
        raise ValueError("shadow policy must explicitly disable execution")
    model_path = Path(str(policy["model_path"]))
    model = lgb.Booster(model_file=str(model_path))
    rows = read_jsonl(root / args.panel)
    scores = model.predict(matrix(rows, model.feature_name()))
    result = select_shadow_candidates(
        rows,
        np.asarray(scores, dtype=float),
        score_cutoff=float(policy["policy"]["score_cutoff"]),
        expected_universe_size=args.expected_universe_size,
        minimum_coverage_fraction=float(
            policy["policy"]["minimum_universe_coverage_fraction"]
        ),
    )
    result.update({
        "build": "ALIENTAI_SELECTIVE_TWO_DAY_SHADOW_SCORER_V1",
        "research_only": True,
        "model_sha256": policy["model_sha256"],
        "horizon_sessions": 2,
    })
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
