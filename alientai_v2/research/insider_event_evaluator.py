from __future__ import annotations

"""Evaluate newly disclosed insider purchases without repeated-row inflation."""

from collections import defaultdict
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from alientai_v2.features.insider_purchase_features import safe_float


def select_event_rows(
    rows: Iterable[Mapping[str, Any]], *, horizon_trading_days: int = 5,
) -> List[Dict[str, Any]]:
    """Keep the first eligible row after new purchases and prevent overlap by symbol."""
    if horizon_trading_days <= 0:
        raise ValueError("horizon_trading_days must be positive")
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("symbol") or "").upper().strip()].append(row)

    events: List[Dict[str, Any]] = []
    for symbol, symbol_rows in grouped.items():
        if not symbol:
            continue
        ordered = sorted(symbol_rows, key=lambda row: str(row.get("market_date") or ""))
        previous_visible = 0
        next_eligible_index = 0
        for index, row in enumerate(ordered):
            visible = int(safe_float(row.get("insider_purchase_total_visible")))
            newly_visible = max(0, visible - previous_visible)
            previous_visible = max(previous_visible, visible)
            if newly_visible <= 0 or index < next_eligible_index:
                continue
            event = dict(row)
            event["newly_visible_purchase_count"] = newly_visible
            events.append(event)
            next_eligible_index = index + horizon_trading_days
    return sorted(events, key=lambda row: (str(row.get("market_date")), str(row.get("symbol"))))


def _value_bucket(row: Mapping[str, Any]) -> str:
    value = safe_float(row.get("insider_total_value_7d"))
    if value >= 500_000:
        return "value_500k_plus"
    if value >= 100_000:
        return "value_100k_to_500k"
    return "value_below_100k"


def event_buckets(row: Mapping[str, Any]) -> List[str]:
    buckets = ["all_events", _value_bucket(row)]
    if bool(row.get("insider_cluster_buy_30d")):
        buckets.append("cluster_buy")
    if safe_float(row.get("insider_officer_buy_count_30d")) > 0:
        buckets.append("officer_buy")
    if safe_float(row.get("insider_director_buy_count_30d")) > 0:
        buckets.append("director_buy")
    if safe_float(row.get("insider_ten_percent_owner_buy_count_30d")) > 0:
        buckets.append("ten_percent_owner_buy")
    if safe_float(row.get("insider_max_ownership_increase_ratio_30d")) >= 0.10:
        buckets.append("ownership_increase_10pct_plus")
    return buckets


def summarize_events(
    events: Sequence[Mapping[str, Any]], *, round_trip_cost_pct: float = 0.25,
) -> List[Dict[str, Any]]:
    if round_trip_cost_pct < 0:
        raise ValueError("round_trip_cost_pct cannot be negative")
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        for bucket in event_buckets(event):
            grouped[bucket].append(event)

    summaries: List[Dict[str, Any]] = []
    for bucket, selected in grouped.items():
        gross = [safe_float(row.get("label_forward_return_5d_pct")) for row in selected]
        excess = [safe_float(row.get("label_excess_return_5d_pct")) for row in selected]
        net = [value - round_trip_cost_pct for value in gross]
        wins = [value > 0.0 for value in net]
        gains = sum(value for value in net if value > 0.0)
        losses = -sum(value for value in net if value < 0.0)
        summaries.append({
            "bucket": bucket,
            "sample_count": len(selected),
            "symbol_count": len({str(row.get("symbol")) for row in selected}),
            "average_gross_return_5d_pct": round(mean(gross), 6),
            "median_gross_return_5d_pct": round(median(gross), 6),
            "average_net_return_5d_pct": round(mean(net), 6),
            "average_excess_return_5d_pct": round(mean(excess), 6),
            "net_win_rate_pct": round(100.0 * sum(wins) / len(wins), 4),
            "profit_factor": round(gains / losses, 6) if losses > 0 else None,
        })
    return sorted(summaries, key=lambda item: (-item["sample_count"], item["bucket"]))


def evaluate_rows(
    rows: Iterable[Mapping[str, Any]], *, horizon_trading_days: int = 5,
    round_trip_cost_pct: float = 0.25,
) -> Dict[str, Any]:
    events = select_event_rows(rows, horizon_trading_days=horizon_trading_days)
    return {
        "event_count": len(events),
        "symbol_count": len({str(row.get("symbol")) for row in events}),
        "horizon_trading_days": horizon_trading_days,
        "round_trip_cost_pct": round_trip_cost_pct,
        "buckets": summarize_events(events, round_trip_cost_pct=round_trip_cost_pct),
    }
