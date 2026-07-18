from __future__ import annotations

"""Regime-Conditional Evidence Fusion (RCEF) research engine.

RCEF is intentionally research-only.  It combines independently produced
specialist signals and historical-analogue evidence, but never emits a live or
paper BUY_CANDIDATE.  A future trained fusion model can replace the transparent
weighted fusion after it passes chronological out-of-sample validation.
"""

from dataclasses import dataclass
from math import exp, sqrt
from statistics import pstdev
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from alientai_v2.engines.base_engine import make_candidate
from alientai_v2.engines.rcef_evidence import build_rcef_evidence


ENGINE_ID = "rcef_research"
SPECIALISTS = ("price", "events", "news", "market")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if number == number else default
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def sigmoid(value: float) -> float:
    value = clamp(value, -30.0, 30.0)
    return 1.0 / (1.0 + exp(-value))


@dataclass(frozen=True)
class SpecialistSignal:
    name: str
    expected_excess_return_pct: float
    probability_up: float
    confidence: float
    freshness: float = 1.0
    available: bool = True

    @classmethod
    def from_mapping(cls, name: str, row: Mapping[str, Any]) -> "SpecialistSignal":
        return cls(
            name=name,
            expected_excess_return_pct=clamp(
                safe_float(row.get("expected_excess_return_pct")), -20.0, 20.0
            ),
            probability_up=clamp(safe_float(row.get("probability_up"), 0.5), 0.0, 1.0),
            confidence=clamp(safe_float(row.get("confidence")), 0.0, 1.0),
            freshness=clamp(safe_float(row.get("freshness"), 1.0), 0.0, 1.0),
            available=bool(row.get("available", True)),
        )


REGIME_WEIGHTS: Dict[str, Dict[str, float]] = {
    "bull_trend": {"price": 0.38, "events": 0.25, "news": 0.15, "market": 0.22},
    "bear_trend": {"price": 0.22, "events": 0.29, "news": 0.18, "market": 0.31},
    "sideways": {"price": 0.25, "events": 0.35, "news": 0.20, "market": 0.20},
    "high_volatility": {"price": 0.18, "events": 0.27, "news": 0.20, "market": 0.35},
    "recovery": {"price": 0.32, "events": 0.23, "news": 0.15, "market": 0.30},
}


def classify_regime(context: Mapping[str, Any]) -> str:
    """Transparent initial router; inputs must be known at prediction time."""
    spy_20d = safe_float(context.get("spy_return_20d_pct"))
    spy_5d = safe_float(context.get("spy_return_5d_pct"))
    vix = safe_float(context.get("vix"), 20.0)
    breadth = safe_float(context.get("breadth_above_50d_pct"), 50.0)

    if vix >= 30.0:
        return "high_volatility"
    if spy_20d <= -5.0 and spy_5d >= 1.0:
        return "recovery"
    if spy_20d >= 2.0 and breadth >= 52.0:
        return "bull_trend"
    if spy_20d <= -2.0 and breadth <= 48.0:
        return "bear_trend"
    return "sideways"


def _active_signals(raw: Mapping[str, Any]) -> List[SpecialistSignal]:
    rows: List[SpecialistSignal] = []
    for name in SPECIALISTS:
        value = raw.get(name)
        if isinstance(value, Mapping):
            signal = SpecialistSignal.from_mapping(name, value)
            if signal.available and signal.confidence > 0.0 and signal.freshness > 0.0:
                rows.append(signal)
    return rows


def evaluate_evidence(
    evidence: Mapping[str, Any],
    settings: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Fuse specialist forecasts, analogues and uncertainty into one verdict."""
    settings = settings or {}
    regime = classify_regime(evidence.get("market_context", {}))
    signals = _active_signals(evidence.get("specialists", {}))
    base_weights = REGIME_WEIGHTS[regime]

    weighted: List[tuple[SpecialistSignal, float]] = []
    for signal in signals:
        effective = base_weights[signal.name] * signal.confidence * signal.freshness
        if effective > 0.0:
            weighted.append((signal, effective))
    weight_sum = sum(weight for _, weight in weighted)

    min_specialists = int(safe_float(settings.get("rcef_min_specialists"), 3.0))
    if len(weighted) < min_specialists or weight_sum <= 0.0:
        return _abstention(regime, "insufficient_specialists", len(weighted))

    expected = sum(s.expected_excess_return_pct * w for s, w in weighted) / weight_sum
    probability = sum(s.probability_up * w for s, w in weighted) / weight_sum
    predictions = [s.expected_excess_return_pct for s, _ in weighted]
    disagreement = pstdev(predictions) if len(predictions) > 1 else 0.0
    agreement = clamp(1.0 - disagreement / 4.0, 0.0, 1.0)

    analog = evidence.get("analogs", {})
    cases = int(safe_float(analog.get("cases")))
    analog_return = safe_float(analog.get("avg_excess_return_pct"))
    analog_win_rate = clamp(safe_float(analog.get("win_rate"), 0.5), 0.0, 1.0)
    min_cases = int(safe_float(settings.get("rcef_min_analog_cases"), 30.0))
    analog_reliability = clamp(cases / max(min_cases * 2.0, 1.0), 0.0, 1.0)

    if cases < min_cases:
        return _abstention(regime, "insufficient_analog_cases", len(weighted), cases=cases)

    analog_agrees = (expected >= 0.0 and analog_return >= 0.0) or (
        expected < 0.0 and analog_return < 0.0
    )
    if not analog_agrees:
        agreement *= 0.45

    blended_return = expected * (1.0 - 0.30 * analog_reliability) + analog_return * (
        0.30 * analog_reliability
    )
    blended_probability = probability * (1.0 - 0.25 * analog_reliability) + analog_win_rate * (
        0.25 * analog_reliability
    )

    downside = max(0.0, safe_float(evidence.get("predicted_drawdown_pct"), 0.0) * -1.0)
    data_quality = clamp(safe_float(evidence.get("data_quality"), 0.0), 0.0, 1.0)
    liquidity = clamp(safe_float(evidence.get("liquidity_score"), 0.0), 0.0, 1.0)
    cost_pct = max(0.0, safe_float(evidence.get("round_trip_cost_pct"), 0.25))
    net_expected = blended_return - cost_pct

    confidence = (
        0.30 * clamp((blended_probability - 0.5) / 0.20, 0.0, 1.0)
        + 0.25 * agreement
        + 0.20 * data_quality
        + 0.15 * liquidity
        + 0.10 * analog_reliability
    )
    risk_adjusted_score = net_expected * confidence / max(1.0, downside)
    calibrated_up_probability = sigmoid((blended_probability - 0.5) * 8.0 * confidence)

    min_net = safe_float(settings.get("rcef_min_expected_net_return_pct"), 0.50)
    min_confidence = safe_float(settings.get("rcef_min_confidence"), 0.65)
    min_agreement = safe_float(settings.get("rcef_min_agreement"), 0.55)
    reasons: List[str] = []
    if net_expected < min_net:
        reasons.append("expected_return_below_margin")
    if confidence < min_confidence:
        reasons.append("confidence_below_minimum")
    if agreement < min_agreement:
        reasons.append("specialists_or_analogs_disagree")
    if data_quality < 0.80:
        reasons.append("data_quality_below_minimum")
    if liquidity < 0.70:
        reasons.append("liquidity_below_minimum")

    eligible = not reasons
    return {
        "engine_id": ENGINE_ID,
        "research_only": True,
        "regime": regime,
        "eligible": eligible,
        "decision": "WATCH" if eligible else "AVOID",
        "abstention_reasons": reasons,
        "specialists_used": [s.name for s, _ in weighted],
        "specialist_count": len(weighted),
        "analog_cases": cases,
        "expected_excess_return_pct": round(blended_return, 6),
        "expected_net_excess_return_pct": round(net_expected, 6),
        "probability_up": round(calibrated_up_probability, 6),
        "confidence": round(confidence, 6),
        "agreement": round(agreement, 6),
        "predicted_drawdown_pct": round(-downside, 6),
        "risk_adjusted_score": round(risk_adjusted_score, 6),
    }


def _abstention(regime: str, reason: str, count: int, cases: int = 0) -> Dict[str, Any]:
    return {
        "engine_id": ENGINE_ID,
        "research_only": True,
        "regime": regime,
        "eligible": False,
        "decision": "AVOID",
        "abstention_reasons": [reason],
        "specialist_count": count,
        "analog_cases": cases,
        "expected_net_excess_return_pct": 0.0,
        "probability_up": 0.5,
        "confidence": 0.0,
        "agreement": 0.0,
        "risk_adjusted_score": 0.0,
    }


def _price(quote: Mapping[str, Any]) -> float:
    for key in ("price", "last", "last_price", "mark", "close"):
        value = safe_float(quote.get(key))
        if value > 0.0:
            return value
    return 0.0


def scan(quotes: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Registry-compatible scan. Evidence is supplied under quote['rcef_evidence']."""
    results: List[Dict[str, Any]] = []
    for quote in quotes:
        symbol = str(quote.get("symbol") or "").upper().strip()
        evidence = quote.get("rcef_evidence")
        if not isinstance(evidence, Mapping) and isinstance(quote.get("rcef_inputs"), Mapping):
            try:
                evidence = build_rcef_evidence(quote["rcef_inputs"])
            except (TypeError, ValueError):
                evidence = None
        if not symbol or not isinstance(evidence, Mapping):
            continue
        verdict = evaluate_evidence(evidence, settings)
        score = clamp(50.0 + verdict["risk_adjusted_score"] * 20.0, 0.0, 100.0)
        reason = (
            f"RCEF research-only; regime={verdict['regime']}; "
            f"net={verdict['expected_net_excess_return_pct']:.3f}%; "
            f"confidence={verdict['confidence']:.3f}; "
            f"agreement={verdict['agreement']:.3f}."
        )
        row = make_candidate(
            engine_id=ENGINE_ID,
            symbol=symbol,
            side="LONG",
            score=score,
            decision=verdict["decision"],
            price=_price(quote),
            prediction_horizon_minutes=5 * 1440,
            minimum_hold_minutes=0,
            reason=reason,
            quote=dict(quote),
            warnings=["RESEARCH_ONLY", *verdict["abstention_reasons"]],
            reasons=[reason],
        )
        row["rcef"] = verdict
        results.append(row)
    return results
