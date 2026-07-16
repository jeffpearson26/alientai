from __future__ import annotations

from typing import Any, Dict, List

from alientai_v2.engines.base_engine import make_candidate
from alientai_v2.utils import safe_float


ENGINE_ID = "momentum_5min"


def scan(quotes: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fast quote-momentum engine.

    Purpose:
    - Catch strong same-day momentum
    - Short prediction horizon
    - Small minimum hold
    """

    candidates: List[Dict[str, Any]] = []

    horizon_minutes = safe_float(settings.get("momentum_5min_horizon_minutes"), 5.0)
    minimum_hold_minutes = safe_float(settings.get("momentum_5min_minimum_hold_minutes"), 5.0)

    use_allowlist = bool(settings.get("momentum_5min_use_replay_allowlist", False))
    allowed_symbols = set(str(x).upper() for x in settings.get("momentum_5min_allowed_symbols", []))

    for quote in quotes:
        symbol = str(quote.get("symbol") or "").upper()

        if use_allowlist and symbol not in allowed_symbols:
            continue
        price = safe_float(quote.get("price"), 0.0)
        move = safe_float(quote.get("net_change_percent"), 0.0)
        rv = safe_float(quote.get("relative_volume"), 1.0)
        spread = safe_float(quote.get("spread_percent"), 99.0)
        volume = safe_float(quote.get("volume"), 0.0)

        score = 0.0
        reasons: List[str] = []
        warnings: List[str] = []

        if price <= 0:
            continue

        if move > 0:
            score += 20
            reasons.append("Positive same-day mover.")
            move_points = min(35.0, move * 5.0)
            score += move_points
            reasons.append(f"Momentum move bonus: +{round(move_points, 2)}.")
        else:
            score -= 25
            warnings.append("Not moving up today.")

        if rv >= 3.0:
            score += 20
            reasons.append("Very strong relative volume.")
        elif rv >= 2.0:
            score += 14
            reasons.append("Strong relative volume.")
        elif rv >= 1.5:
            score += 8
            reasons.append("Moderate relative volume.")
        elif rv > 1.05:
            score += 3
            reasons.append("Slight relative-volume boost.")
        else:
            reasons.append("Relative volume neutral or unavailable.")

        if volume >= 10_000_000:
            score += 8
            reasons.append("Very liquid.")
        elif volume >= 2_000_000:
            score += 5
            reasons.append("Liquid.")
        elif volume >= 500_000:
            score += 2
            reasons.append("Usable volume.")
        elif volume > 0:
            score -= 5
            warnings.append("Low volume.")

        if spread <= 0.03:
            score += 12
            reasons.append("Excellent spread.")
        elif spread <= 0.10:
            score += 9
            reasons.append("Very tight spread.")
        elif spread <= 0.20:
            score += 5
            reasons.append("Acceptable spread.")
        elif spread <= 0.35:
            score += 1
            warnings.append("Spread is a little wide.")
        else:
            score -= 25
            warnings.append("Spread too wide.")

        if price < 2:
            score -= 30
            warnings.append("Sub-$2 price risk.")
        elif price < 5:
            score -= 10
            warnings.append("Low-priced stock risk.")

        score = max(0.0, min(100.0, score))

        if score >= 75:
            decision = "STRONG_BUY_CANDIDATE"
        elif score >= 55:
            decision = "BUY_CANDIDATE"
        elif score >= 40:
            decision = "WATCH"
        else:
            decision = "AVOID"

        candidates.append(
            make_candidate(
                engine_id=ENGINE_ID,
                symbol=symbol,
                side="LONG",
                score=score,
                decision=decision,
                price=price,
                prediction_horizon_minutes=horizon_minutes,
                minimum_hold_minutes=minimum_hold_minutes,
                reason="Fast 5-minute momentum candidate.",
                quote=quote,
                warnings=warnings,
                reasons=reasons,
            )
        )

    candidates.sort(key=lambda row: row.get("score", 0), reverse=True)
    return candidates

