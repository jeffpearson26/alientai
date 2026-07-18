from __future__ import annotations

"""Point-in-time evidence construction for the RCEF research engine."""

from datetime import datetime, timezone
from math import sqrt
from statistics import pstdev
from typing import Any, Dict, Iterable, List, Mapping, Sequence


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if number == number else default
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def timestamp_ms(value: Any) -> int:
    if isinstance(value, (int, float)):
        number = int(value)
        return number if number > 10_000_000_000 else number * 1000
    text = str(value or "").strip()
    if not text:
        return 0
    if text.isdigit():
        return timestamp_ms(int(text))
    text = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y%m%dT%H%M%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def row_timestamp_ms(row: Mapping[str, Any]) -> int:
    for key in (
        "available_at", "published_at", "time_published", "filed_at",
        "announced_at", "datetime_utc", "datetime_ms", "timestamp", "date",
    ):
        value = row.get(key)
        if value not in (None, ""):
            parsed = timestamp_ms(value)
            if parsed:
                return parsed
    return 0


def point_in_time_rows(rows: Iterable[Mapping[str, Any]], as_of: Any) -> List[Mapping[str, Any]]:
    cutoff = timestamp_ms(as_of)
    if cutoff <= 0:
        raise ValueError("RCEF evidence requires a valid as_of timestamp")
    accepted = []
    for row in rows:
        when = row_timestamp_ms(row)
        if 0 < when <= cutoff:
            accepted.append(row)
    return sorted(accepted, key=row_timestamp_ms)


def _close(row: Mapping[str, Any]) -> float:
    return safe_float(row.get("close"))


def _return_pct(old: float, new: float) -> float:
    return ((new / old) - 1.0) * 100.0 if old > 0.0 and new > 0.0 else 0.0


def build_price_specialist(
    candles: Sequence[Mapping[str, Any]],
    benchmark_candles: Sequence[Mapping[str, Any]],
    as_of: Any,
    premarket: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    rows = point_in_time_rows(candles, as_of)
    benchmark = point_in_time_rows(benchmark_candles, as_of)
    if len(rows) < 21 or len(benchmark) < 21:
        return {"available": False, "confidence": 0.0}

    closes = [_close(row) for row in rows if _close(row) > 0.0]
    bench_closes = [_close(row) for row in benchmark if _close(row) > 0.0]
    if len(closes) < 21 or len(bench_closes) < 21:
        return {"available": False, "confidence": 0.0}

    ret_5 = _return_pct(closes[-6], closes[-1])
    ret_20 = _return_pct(closes[-21], closes[-1])
    benchmark_5 = _return_pct(bench_closes[-6], bench_closes[-1])
    benchmark_20 = _return_pct(bench_closes[-21], bench_closes[-1])
    excess_5 = ret_5 - benchmark_5
    excess_20 = ret_20 - benchmark_20
    daily_returns = [_return_pct(closes[i - 1], closes[i]) for i in range(len(closes) - 19, len(closes))]
    volatility = pstdev(daily_returns) * sqrt(5.0) if len(daily_returns) > 1 else 0.0

    premarket_move = 0.0
    premarket_volume_score = 0.0
    if premarket:
        premarket_move = clamp(safe_float(premarket.get("move_pct")), -10.0, 10.0)
        premarket_volume_score = clamp(safe_float(premarket.get("relative_volume")) / 3.0, 0.0, 1.0)

    expected = 0.42 * excess_5 + 0.18 * excess_20 + 0.20 * premarket_move
    expected = clamp(expected, -8.0, 8.0)
    probability = clamp(0.5 + expected / max(12.0, volatility * 5.0), 0.05, 0.95)
    confidence = clamp(0.55 + min(len(closes), 252) / 1260.0 + 0.10 * premarket_volume_score, 0.0, 0.90)
    return {
        "available": True,
        "expected_excess_return_pct": expected,
        "probability_up": probability,
        "confidence": confidence,
        "freshness": 1.0,
        "diagnostics": {
            "return_5d_pct": ret_5, "return_20d_pct": ret_20,
            "excess_5d_pct": excess_5, "excess_20d_pct": excess_20,
            "five_day_volatility_pct": volatility, "premarket_move_pct": premarket_move,
        },
    }


def build_event_specialist(events: Sequence[Mapping[str, Any]], as_of: Any) -> Dict[str, Any]:
    cutoff = timestamp_ms(as_of)
    rows = point_in_time_rows(events, as_of)
    contributions: List[float] = []
    used: List[str] = []
    for row in rows:
        kind = str(row.get("event_type") or row.get("type") or "").lower().strip()
        age_days = max(0.0, (cutoff - row_timestamp_ms(row)) / 86_400_000.0)
        freshness = clamp(1.0 - age_days / 90.0, 0.0, 1.0)
        impact = 0.0
        if kind in {"insider_purchase", "insider_buy", "open_market_purchase"}:
            value = safe_float(row.get("transaction_value") or row.get("value"))
            impact = clamp(0.35 + value / 2_000_000.0, 0.35, 1.50)
        elif kind in {"rating_upgrade", "analyst_upgrade"}:
            before = str(row.get("from_rating") or "").lower()
            after = str(row.get("to_rating") or "").lower()
            impact = 1.15 if "hold" in before and "buy" in after else 0.65
        elif kind in {"earnings_beat", "guidance_raise", "revenue_beat"}:
            impact = clamp(safe_float(row.get("impact"), 0.70), 0.20, 1.50)
        elif kind in {"insider_sale", "insider_sell"}:
            continue
        if impact > 0.0 and freshness > 0.0:
            contributions.append(impact * freshness)
            used.append(kind)

    if not contributions:
        return {"available": False, "confidence": 0.0, "diagnostics": {"events_used": []}}
    expected = clamp(sum(contributions), 0.0, 4.0)
    return {
        "available": True,
        "expected_excess_return_pct": expected,
        "probability_up": clamp(0.5 + expected / 10.0, 0.5, 0.90),
        "confidence": clamp(0.45 + 0.10 * len(contributions), 0.0, 0.88),
        "freshness": 1.0,
        "diagnostics": {"events_used": used, "positive_event_count": len(used)},
    }


def build_news_specialist(news: Sequence[Mapping[str, Any]], as_of: Any) -> Dict[str, Any]:
    cutoff = timestamp_ms(as_of)
    rows = point_in_time_rows(news, as_of)
    weighted_sum = 0.0
    weight_sum = 0.0
    for row in rows[-50:]:
        age_days = max(0.0, (cutoff - row_timestamp_ms(row)) / 86_400_000.0)
        freshness = clamp(1.0 - age_days / 14.0, 0.0, 1.0)
        relevance = clamp(safe_float(row.get("ticker_relevance_score"), 0.5), 0.0, 1.0)
        novelty = clamp(safe_float(row.get("novelty"), 1.0), 0.0, 1.0)
        weight = freshness * max(0.10, relevance) * novelty
        sentiment = clamp(safe_float(row.get("ticker_sentiment_score") or row.get("sentiment")), -1.0, 1.0)
        weighted_sum += sentiment * weight
        weight_sum += weight
    if weight_sum <= 0.0:
        return {"available": False, "confidence": 0.0}
    score = weighted_sum / weight_sum
    return {
        "available": True,
        "expected_excess_return_pct": clamp(score * 2.0, -2.0, 2.0),
        "probability_up": clamp(0.5 + score * 0.25, 0.20, 0.80),
        "confidence": clamp(0.35 + min(weight_sum, 5.0) / 10.0, 0.0, 0.82),
        "freshness": 1.0,
        "diagnostics": {"articles_used": len(rows[-50:]), "weighted_sentiment": score},
    }


def build_market_specialist(context: Mapping[str, Any]) -> Dict[str, Any]:
    spy_20 = safe_float(context.get("spy_return_20d_pct"))
    breadth = safe_float(context.get("breadth_above_50d_pct"), 50.0)
    sector_relative = safe_float(context.get("sector_relative_20d_pct"))
    vix = safe_float(context.get("vix"), 20.0)
    expected = 0.08 * spy_20 + 0.06 * sector_relative + 0.012 * (breadth - 50.0) - 0.025 * max(0.0, vix - 22.0)
    return {
        "available": True,
        "expected_excess_return_pct": clamp(expected, -3.0, 3.0),
        "probability_up": clamp(0.5 + expected / 8.0, 0.15, 0.85),
        "confidence": 0.70,
        "freshness": 1.0,
    }


def build_rcef_evidence(inputs: Mapping[str, Any]) -> Dict[str, Any]:
    as_of = inputs.get("as_of")
    if timestamp_ms(as_of) <= 0:
        raise ValueError("RCEF inputs require as_of")
    context = inputs.get("market_context") if isinstance(inputs.get("market_context"), Mapping) else {}
    specialists = {
        "price": build_price_specialist(inputs.get("candles", []), inputs.get("benchmark_candles", []), as_of, inputs.get("premarket")),
        "events": build_event_specialist(inputs.get("events", []), as_of),
        "news": build_news_specialist(inputs.get("news", []), as_of),
        "market": build_market_specialist(context),
    }
    available = sum(bool(row.get("available")) for row in specialists.values())
    return {
        "as_of": as_of,
        "market_context": dict(context),
        "specialists": specialists,
        "analogs": dict(inputs.get("analogs") or {}),
        "predicted_drawdown_pct": safe_float(inputs.get("predicted_drawdown_pct")),
        "data_quality": clamp(available / 4.0, 0.0, 1.0),
        "liquidity_score": clamp(safe_float(inputs.get("liquidity_score")), 0.0, 1.0),
        "round_trip_cost_pct": max(0.0, safe_float(inputs.get("round_trip_cost_pct"), 0.25)),
    }
