"""Fail-closed policy for a future selective five-day research model.

This module does not train or load a model, contact a data provider, write
settings, or place an order.  It is the decision contract for scored rows
produced by separately validated classifiers and quantile regressors.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping


POLICY_ID = "selective_five_day_catalyst_v1"
REQUIRED_POLICY_FIELDS = (
    "minimum_universe_size",
    "minimum_profit_probability",
    "minimum_large_move_probability",
    "minimum_expected_net_return_pct",
    "minimum_lower_quantile_net_return_pct",
    "maximum_model_disagreement",
    "round_trip_cost_pct",
)
SCORE_FIELDS = (
    "calibrated_profit_probability",
    "calibrated_large_move_probability",
    "expected_net_return_pct",
    "lower_quantile_net_return_pct",
    "model_disagreement",
)


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def validate_policy(policy: Mapping[str, Any]) -> dict[str, float | int]:
    """Validate thresholds that must have been frozen using validation data."""
    missing = [name for name in REQUIRED_POLICY_FIELDS if name not in policy]
    if missing:
        raise ValueError(f"policy is missing required fields: {', '.join(missing)}")

    minimum_universe_size = policy["minimum_universe_size"]
    if isinstance(minimum_universe_size, bool) or not isinstance(minimum_universe_size, int):
        raise ValueError("minimum_universe_size must be an integer")
    if minimum_universe_size < 1:
        raise ValueError("minimum_universe_size must be positive")

    numbers: dict[str, float | int] = {"minimum_universe_size": minimum_universe_size}
    for name in REQUIRED_POLICY_FIELDS[1:]:
        value = _finite_number(policy[name])
        if value is None:
            raise ValueError(f"{name} must be a finite number")
        numbers[name] = value

    for name in ("minimum_profit_probability", "minimum_large_move_probability", "maximum_model_disagreement"):
        if not 0.0 <= float(numbers[name]) <= 1.0:
            raise ValueError(f"{name} must be between zero and one")
    if float(numbers["round_trip_cost_pct"]) < 0.0:
        raise ValueError("round_trip_cost_pct cannot be negative")
    return numbers


def evaluate_selective_five_day_panel(
    rows: Iterable[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one complete same-day panel and abstain on missing evidence.

    Every passing row is retained; there is intentionally no daily or weekly
    quota.  This lets zero, one, or several independently qualified candidates
    survive without lowering the threshold merely to produce a prediction.
    """
    rules = validate_policy(policy)
    source_rows = list(rows)
    market_dates = {str(row.get("market_date") or "").strip() for row in source_rows}
    if "" in market_dates:
        raise ValueError("every row must have a market_date")
    if len(market_dates) != 1:
        raise ValueError("policy input must contain exactly one market date")

    symbols: set[str] = set()
    normalized: list[tuple[Mapping[str, Any], str]] = []
    for row in source_rows:
        symbol = str(row.get("symbol") or "").upper().strip()
        if not symbol:
            raise ValueError("every row must have a symbol")
        if symbol in symbols:
            raise ValueError(f"duplicate symbol in same-day panel: {symbol}")
        symbols.add(symbol)
        normalized.append((row, symbol))

    market_date = next(iter(market_dates))
    if len(symbols) < int(rules["minimum_universe_size"]):
        return {
            "policy_id": POLICY_ID,
            "status": "INCOMPLETE_PANEL",
            "research_only": True,
            "execution_enabled": False,
            "market_date": market_date,
            "universe_size": len(symbols),
            "policy": rules,
            "candidates": [],
            "rejections": [],
            "failure_reasons": ["minimum universe size not met"],
        }

    candidates: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    for row, symbol in normalized:
        values = {name: _finite_number(row.get(name)) for name in SCORE_FIELDS}
        reasons: list[str] = []
        if row.get("data_complete") is not True:
            reasons.append("incomplete point-in-time data")
        if row.get("technical_options_agree") is not True:
            reasons.append("technical/options evidence does not agree")
        for name, value in values.items():
            if value is None:
                reasons.append(f"missing {name}")

        if not reasons:
            if values["calibrated_profit_probability"] < float(rules["minimum_profit_probability"]):
                reasons.append("profit probability below threshold")
            if values["calibrated_large_move_probability"] < float(rules["minimum_large_move_probability"]):
                reasons.append("large-move probability below threshold")
            if values["expected_net_return_pct"] < float(rules["minimum_expected_net_return_pct"]):
                reasons.append("expected net return below threshold")
            if values["lower_quantile_net_return_pct"] < float(rules["minimum_lower_quantile_net_return_pct"]):
                reasons.append("lower return estimate below threshold")
            if values["model_disagreement"] > float(rules["maximum_model_disagreement"]):
                reasons.append("model disagreement above threshold")

        if reasons:
            rejections.append({"symbol": symbol, "reasons": reasons})
            continue

        candidates.append({
            **row,
            "symbol": symbol,
            "engine_id": POLICY_ID,
            "decision": "AVOID",
            "shadow_research_decision": "BUY_CANDIDATE",
            "prediction_horizon_trading_days": 5,
            "entry_assumption": "next_regular_session_open",
            "exit_assumption": "fifth_regular_session_close",
            "round_trip_cost_pct": float(rules["round_trip_cost_pct"]),
            "reason": "Research-only: calibrated direction, large-move, return, uncertainty, and agreement gates passed.",
        })

    candidates.sort(
        key=lambda row: (
            -float(row["calibrated_profit_probability"]),
            -float(row["expected_net_return_pct"]),
            row["symbol"],
        )
    )
    return {
        "policy_id": POLICY_ID,
        "status": "RESEARCH_CANDIDATES" if candidates else "ABSTAIN",
        "research_only": True,
        "execution_enabled": False,
        "market_date": market_date,
        "universe_size": len(symbols),
        "policy": rules,
        "candidates": candidates,
        "rejections": rejections,
        "failure_reasons": [],
    }
