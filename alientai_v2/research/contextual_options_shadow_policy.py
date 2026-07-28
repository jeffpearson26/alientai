"""Pure research-only policy for prospective contextual-options shadow signals.

It intentionally has no broker, order, settings-write, or network dependency.
An integration must supply a same-day, point-in-time complete universe of
technical scores and unusual-call flags before it may journal candidates.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

import numpy as np


POLICY_ID = "contextual_options_shadow_v1"
TECHNICAL_TOP_FRACTION = 0.25
MAX_DAILY_CANDIDATES = 5


def _score(row: Mapping[str, Any]) -> float | None:
    value = row.get("technical_context_score")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if np.isfinite(result) else None


def select_shadow_candidates(rows: Iterable[Mapping[str, Any]], top_fraction: float = TECHNICAL_TOP_FRACTION, max_candidates: int = MAX_DAILY_CANDIDATES) -> list[dict[str, Any]]:
    """Select at most five research candidates from a complete same-day universe.

    Missing score or unusual-call status fails closed.  A caller must pass one
    market date only; mixing dates silently changes the percentile meaning and
    is rejected.
    """
    if not 0 < top_fraction <= 1:
        raise ValueError("top_fraction must be in (0, 1]")
    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    source_rows = list(rows)
    normalized = []
    days = set()
    for row in source_rows:
        score = _score(row)
        day = str(row.get("market_date") or "")
        if not day:
            continue
        days.add(day)
        if score is None or row.get("call_volume_unusual") is not True:
            continue
        symbol = str(row.get("symbol") or "").upper().strip()
        if symbol:
            normalized.append({**row, "symbol": symbol, "technical_context_score": score})
    if len(days) > 1:
        raise ValueError("policy input must contain exactly one market date")
    all_scores = [_score(row) for row in source_rows]
    valid_scores = [score for score in all_scores if score is not None]
    if not valid_scores:
        return []
    ordered_scores = np.sort(np.asarray(valid_scores, dtype=float))

    def confidence_rank(score: float) -> int:
        # Cross-sectional percentile rank, deliberately not a probability.
        if len(ordered_scores) == 1:
            return 100
        below_or_equal = int(np.searchsorted(ordered_scores, score, side="right"))
        percentile = 1.0 + 99.0 * (below_or_equal - 1) / (len(ordered_scores) - 1)
        return max(1, min(100, int(round(percentile))))

    cutoff = float(np.quantile(np.asarray(valid_scores), 1.0 - top_fraction))
    chosen = sorted((row for row in normalized if row["technical_context_score"] >= cutoff), key=lambda row: (-row["technical_context_score"], row["symbol"]))[:max_candidates]
    return [{
        **row,
        "engine_id": POLICY_ID,
        "decision": "AVOID",
        "shadow_research_decision": "BUY_CANDIDATE",
        "shadow_policy_id": POLICY_ID,
        "shadow_policy_top_fraction": top_fraction,
        "shadow_policy_score_cutoff": cutoff,
        "confidence_rank_1_to_100": confidence_rank(row["technical_context_score"]),
        "confidence_rank_definition": "same-day eligible-universe model-score percentile; not probability",
        "prediction_horizon_days": 5,
        "reason": "Research-only: unusual public call activity within the daily top technical-score context.",
    } for row in chosen]
