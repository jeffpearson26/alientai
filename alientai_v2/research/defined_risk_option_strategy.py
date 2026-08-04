from __future__ import annotations

"""Deterministic strategy layer for a future learned options-volatility model.

The learned heads must estimate direction, realized movement, and volatility.
This layer converts those frozen estimates into a defined-risk structure or an
honest abstention. It has no broker or order path.
"""

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any


ALLOWED_STACK_ROLES = {
    "merchant_accelerator",
    "memory_hbm",
    "foundry_packaging",
    "semiconductor_equipment",
    "custom_asic_networking",
    "design_software",
    "ai_infrastructure",
    "emerging_inference_specialist",
}

DEFINED_RISK_STRATEGIES = {
    "bull_call_debit_spread",
    "bear_put_debit_spread",
    "bull_put_credit_spread",
    "bear_call_credit_spread",
    "long_straddle",
    "iron_condor",
    "iron_butterfly",
    "calendar_spread",
}


@dataclass(frozen=True)
class OptionStrategyInputs:
    symbol: str
    stack_role: str
    direction_score: float
    expected_absolute_move_pct: float
    implied_move_pct: float
    iv_rank: float
    front_to_back_iv_ratio: float
    technical_confirmation: float
    range_bound_confidence: float
    catalyst_within_five_sessions: bool
    binary_event_within_five_sessions: bool
    liquidity_score: float
    existing_same_stack_risk_pct: float = 0.0


@dataclass(frozen=True)
class OptionStrategyDecision:
    symbol: str
    decision: str
    strategy: str | None
    rationale: tuple[str, ...]
    maximum_portfolio_risk_pct: float
    construction: dict[str, Any]
    research_only: bool = True
    execution_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate(inputs: OptionStrategyInputs) -> None:
    if not inputs.symbol.strip():
        raise ValueError("symbol is required")
    if inputs.stack_role not in ALLOWED_STACK_ROLES:
        raise ValueError(f"unsupported AI-stack role: {inputs.stack_role}")
    bounded = {
        "direction_score": (-1.0, 1.0),
        "iv_rank": (0.0, 1.0),
        "technical_confirmation": (0.0, 1.0),
        "range_bound_confidence": (0.0, 1.0),
        "liquidity_score": (0.0, 1.0),
        "existing_same_stack_risk_pct": (0.0, 100.0),
    }
    for name, (minimum, maximum) in bounded.items():
        value = float(getattr(inputs, name))
        if not isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
    for name in (
        "expected_absolute_move_pct",
        "implied_move_pct",
        "front_to_back_iv_ratio",
    ):
        value = float(getattr(inputs, name))
        if not isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be positive")


def _construction(strategy: str) -> dict[str, Any]:
    common = {
        "expiration_policy": "first liquid expiration after the five-session exit",
        "minimum_open_interest": 100,
        "maximum_leg_spread_pct": 10.0,
        "entry_fill": "buy at ask and sell at bid",
        "exit_fill": "sell at bid and buy back at ask",
    }
    rules = {
        "bull_call_debit_spread": {
            "long_leg": "call delta 0.55-0.70",
            "short_leg": "higher-strike call delta 0.25-0.40",
        },
        "bear_put_debit_spread": {
            "long_leg": "put absolute delta 0.55-0.70",
            "short_leg": "lower-strike put absolute delta 0.25-0.40",
        },
        "bull_put_credit_spread": {
            "short_leg": "put absolute delta 0.20-0.30",
            "long_leg": "lower-strike put absolute delta 0.05-0.15",
        },
        "bear_call_credit_spread": {
            "short_leg": "call delta 0.20-0.30",
            "long_leg": "higher-strike call delta 0.05-0.15",
        },
        "long_straddle": {
            "legs": "buy nearest-strike call and put",
            "maximum_loss": "total debit",
        },
        "iron_condor": {
            "short_put": "absolute delta 0.20-0.30",
            "long_put": "lower strike, absolute delta 0.05-0.15",
            "short_call": "delta 0.20-0.30",
            "long_call": "higher strike, delta 0.05-0.15",
        },
        "iron_butterfly": {
            "short_legs": "nearest-strike call and put",
            "long_wings": "equidistant liquid call and put wings",
        },
        "calendar_spread": {
            "short_leg": "near-term nearest-strike option",
            "long_leg": "same type/strike, later expiration",
            "management": "close before short-leg expiration",
        },
    }
    return {**common, **rules[strategy]}


def choose_defined_risk_strategy(
    inputs: OptionStrategyInputs,
) -> OptionStrategyDecision:
    _validate(inputs)
    emerging = inputs.stack_role == "emerging_inference_specialist"
    maximum_risk = 0.50 if emerging else 1.00
    if inputs.existing_same_stack_risk_pct >= 1.5:
        maximum_risk *= 0.5

    if inputs.liquidity_score < 0.60:
        return OptionStrategyDecision(
            symbol=inputs.symbol,
            decision="ABSTAIN",
            strategy=None,
            rationale=("insufficient multi-leg liquidity",),
            maximum_portfolio_risk_pct=0.0,
            construction={},
        )

    realized_to_implied = (
        inputs.expected_absolute_move_pct / inputs.implied_move_pct
    )
    directional = abs(inputs.direction_score) >= 0.35
    strongly_directional = (
        abs(inputs.direction_score) >= 0.65
        and inputs.technical_confirmation >= 0.60
    )

    strategy: str | None = None
    rationale: list[str] = []

    if realized_to_implied >= 1.20:
        if strongly_directional:
            strategy = (
                "bull_call_debit_spread"
                if inputs.direction_score > 0
                else "bear_put_debit_spread"
            )
            rationale.extend((
                "forecast realized move exceeds implied move",
                "direction and technical setup agree",
            ))
        elif not directional:
            strategy = "long_straddle"
            rationale.extend((
                "forecast realized move exceeds implied move",
                "directional confidence is deliberately low",
            ))
    elif (
        realized_to_implied <= 0.75
        and inputs.iv_rank >= 0.65
        and not inputs.binary_event_within_five_sessions
    ):
        if (
            inputs.front_to_back_iv_ratio >= 1.15
            and inputs.range_bound_confidence >= 0.60
        ):
            strategy = "calendar_spread"
            rationale.extend((
                "front-month volatility is rich to back-month volatility",
                "range-bound forecast supports front decay",
            ))
        elif inputs.range_bound_confidence >= 0.80:
            strategy = "iron_butterfly"
            rationale.extend((
                "implied move appears materially rich",
                "very high pin/range confidence",
            ))
        elif inputs.range_bound_confidence >= 0.60:
            strategy = "iron_condor"
            rationale.extend((
                "implied move appears materially rich",
                "defined-risk range trade",
            ))
        elif strongly_directional:
            strategy = (
                "bull_put_credit_spread"
                if inputs.direction_score > 0
                else "bear_call_credit_spread"
            )
            rationale.extend((
                "implied volatility is rich",
                "directional credit spread keeps risk defined",
            ))

    if strategy is None:
        return OptionStrategyDecision(
            symbol=inputs.symbol,
            decision="ABSTAIN",
            strategy=None,
            rationale=("no sufficiently large direction or volatility edge",),
            maximum_portfolio_risk_pct=0.0,
            construction={},
        )
    if strategy not in DEFINED_RISK_STRATEGIES:
        raise AssertionError("strategy policy emitted an undefined-risk structure")
    if emerging:
        rationale.append("emerging specialist receives half-size risk ceiling")
    if inputs.catalyst_within_five_sessions:
        rationale.append("public catalyst is inside the five-session window")
    return OptionStrategyDecision(
        symbol=inputs.symbol,
        decision="RESEARCH_CANDIDATE",
        strategy=strategy,
        rationale=tuple(rationale),
        maximum_portfolio_risk_pct=maximum_risk,
        construction=_construction(strategy),
    )

