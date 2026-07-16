from __future__ import annotations

from typing import Any, Dict, List

from alientai_v2.utils import safe_float


def score_v2_candidate(quote: Dict[str, Any]) -> Dict[str, Any]:
    symbol = str(quote.get("symbol") or "").upper()
    price = safe_float(quote.get("price"), 0.0)
    move = safe_float(quote.get("net_change_percent"), 0.0)
    rv = safe_float(quote.get("relative_volume"), 1.0)
    spread = safe_float(quote.get("spread_percent"), 99.0)
    volume = safe_float(quote.get("volume"), 0.0)

    reasons: List[str] = []
    warnings: List[str] = []
    score = 0.0

    if price <= 0:
        return {
            "symbol": symbol,
            "price": price,
            "score": 0.0,
            "move_pct": move,
            "relative_volume": rv,
            "spread_percent": spread,
            "volume": volume,
            "source": quote.get("source"),
            "decision": "BLOCK",
            "reasons": [],
            "warnings": ["Invalid or missing price."],
        }

    if move > 0:
        score += 20
        reasons.append("Positive mover.")
        move_points = min(35.0, move * 5.0)
        score += move_points
        reasons.append(f"Move bonus: +{round(move_points, 2)} from {round(move, 3)}% move.")
    else:
        score -= 25
        warnings.append("Not a positive mover.")

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
        reasons.append("Slightly elevated relative volume.")
    else:
        reasons.append("Relative volume neutral or unavailable.")

    if volume >= 10_000_000:
        score += 8
        reasons.append("Very liquid: volume over 10M.")
    elif volume >= 2_000_000:
        score += 5
        reasons.append("Liquid: volume over 2M.")
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
        warnings.append("Spread is too wide.")

    if price < 2:
        score -= 30
        warnings.append("Sub-$2 price blocked/penalized.")
    elif price < 5:
        score -= 10
        warnings.append("Low-priced stock; extra noise risk.")

    score = max(0.0, min(100.0, score))

    if score >= 75:
        decision = "STRONG_BUY_CANDIDATE"
    elif score >= 55:
        decision = "BUY_CANDIDATE"
    elif score >= 40:
        decision = "WATCH"
    else:
        decision = "AVOID"

    return {
        "symbol": symbol,
        "price": round(price, 4),
        "score": round(score, 2),
        "move_pct": round(move, 4),
        "relative_volume": round(rv, 4),
        "spread_percent": round(spread, 4),
        "volume": volume,
        "source": quote.get("source"),
        "decision": decision,
        "reasons": reasons,
        "warnings": warnings,
    }
