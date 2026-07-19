from __future__ import annotations

"""Evaluate distinct point-in-time earnings disclosures without daily-row inflation."""

from collections import defaultdict
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Mapping, Sequence


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if number == number else default
    except (TypeError, ValueError):
        return default


def select_event_rows(rows: Iterable[Mapping[str, Any]], horizon_trading_days: int = 5) -> List[Dict[str, Any]]:
    if horizon_trading_days <= 0:
        raise ValueError("horizon_trading_days must be positive")
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("symbol") or "").upper().strip()].append(row)
    events: List[Dict[str, Any]] = []
    for symbol, symbol_rows in grouped.items():
        ordered = sorted(symbol_rows, key=lambda row: str(row.get("market_date") or ""))
        prior_count = 0
        baseline_established = False
        next_eligible_index = 0
        for index, row in enumerate(ordered):
            count = int(_number(row.get("earnings_visible_quarter_count")))
            if not baseline_established:
                prior_count = count
                baseline_established = True
                continue
            new_count = max(0, count - prior_count)
            prior_count = max(prior_count, count)
            if new_count <= 0 or index < next_eligible_index:
                continue
            event = dict(row)
            event["newly_visible_earnings_count"] = new_count
            events.append(event)
            next_eligible_index = index + horizon_trading_days
    return sorted(events, key=lambda row: (str(row.get("market_date")), str(row.get("symbol"))))


def event_buckets(row: Mapping[str, Any]) -> List[str]:
    buckets = ["all_events"]
    raw = row.get("earnings_surprise_percentage")
    if raw is None:
        buckets.append("surprise_missing")
    else:
        surprise = _number(raw)
        if surprise < 0:
            buckets.append("eps_miss")
        elif surprise == 0:
            buckets.append("eps_met")
        elif surprise < 10:
            buckets.append("eps_beat_0_to_10pct")
        elif surprise < 25:
            buckets.append("eps_beat_10_to_25pct")
        else:
            buckets.append("eps_beat_25pct_plus")
    if int(_number(row.get("earnings_beat_streak"))) >= 2:
        buckets.append("beat_streak_2_plus")
    return buckets


def summarize(events: Sequence[Mapping[str, Any]], round_trip_cost_pct: float = 0.25) -> List[Dict[str, Any]]:
    if round_trip_cost_pct < 0:
        raise ValueError("round_trip_cost_pct cannot be negative")
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        for bucket in event_buckets(event):
            grouped[bucket].append(event)
    output = []
    for bucket, selected in grouped.items():
        gross = [_number(row.get("label_forward_return_5d_pct")) for row in selected]
        net = [value - round_trip_cost_pct for value in gross]
        excess = [_number(row.get("label_excess_return_5d_pct")) for row in selected]
        gains = sum(value for value in net if value > 0)
        losses = -sum(value for value in net if value < 0)
        output.append({
            "bucket": bucket,
            "sample_count": len(selected),
            "symbol_count": len({str(row.get("symbol")) for row in selected}),
            "average_net_return_5d_pct": round(mean(net), 6),
            "median_net_return_5d_pct": round(median(net), 6),
            "average_excess_return_5d_pct": round(mean(excess), 6),
            "net_win_rate_pct": round(100.0 * sum(value > 0 for value in net) / len(net), 4),
            "profit_factor": round(gains / losses, 6) if losses > 0 else None,
        })
    return sorted(output, key=lambda row: (-row["sample_count"], row["bucket"]))


def evaluate_rows(
    rows: Iterable[Mapping[str, Any]], horizon_trading_days: int = 5,
    round_trip_cost_pct: float = 0.25,
) -> Dict[str, Any]:
    events = select_event_rows(rows, horizon_trading_days)
    return {
        "research_only": True,
        "execution_enabled": False,
        "event_count": len(events),
        "symbol_count": len({str(row.get("symbol")) for row in events}),
        "horizon_trading_days": horizon_trading_days,
        "round_trip_cost_pct": round_trip_cost_pct,
        "buckets": summarize(events, round_trip_cost_pct),
    }
