from __future__ import annotations

"""Matched retrospective study of pre-move winner conditions."""

from collections import defaultdict
from datetime import date
from math import log1p
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from alientai_v2.features.insider_purchase_features import safe_float


DEFAULT_ANALYSIS_FEATURES = (
    "return_5d_lag_pct", "return_20d_lag_pct", "return_60d_lag_pct",
    "realized_volatility_20d_pct",
    "insider_purchase_count_7d", "insider_purchase_count_30d",
    "insider_unique_buyers_30d", "insider_total_value_30d",
    "insider_max_purchase_value_30d", "insider_max_ownership_increase_ratio_30d",
    "technical_rsi_2", "technical_rsi_14",
    "technical_ema9_distance_pct", "technical_ema21_distance_pct", "technical_ema50_distance_pct",
    "technical_macd_pct", "technical_macd_signal_pct", "technical_macd_histogram_pct",
    "technical_atr14_pct", "technical_adx14", "technical_plus_di14", "technical_minus_di14",
    "technical_bollinger_width_pct", "technical_bollinger_position",
    "technical_relative_volume_10_vs_20", "technical_latest_relative_volume_20",
    "technical_obv_change_10d_normalized", "technical_positive_days_10d",
    "technical_max_daily_return_10d_pct", "technical_min_daily_return_10d_pct",
    "technical_volatility_compression_ratio",
)


def _day(row: Mapping[str, Any]) -> date:
    return date.fromisoformat(str(row.get("market_date") or "")[:10])


def _symbol(row: Mapping[str, Any]) -> str:
    return str(row.get("symbol") or "").upper().strip()


def select_non_overlapping_winners(
    rows: Iterable[Mapping[str, Any]], *, winner_return_pct: float = 5.0,
    minimum_calendar_gap_days: int = 9,
) -> List[Mapping[str, Any]]:
    if winner_return_pct <= 0 or minimum_calendar_gap_days < 0:
        raise ValueError("invalid winner threshold or gap")
    by_symbol: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if _symbol(row) and safe_float(row.get("label_forward_return_5d_pct")) >= winner_return_pct:
            by_symbol[_symbol(row)].append(row)
    winners: List[Mapping[str, Any]] = []
    for symbol_rows in by_symbol.values():
        previous_day: date | None = None
        for row in sorted(symbol_rows, key=_day):
            current_day = _day(row)
            if previous_day is not None and (current_day - previous_day).days < minimum_calendar_gap_days:
                continue
            winners.append(row)
            previous_day = current_day
    return sorted(winners, key=lambda row: (_day(row), _symbol(row)))


def match_distance(winner: Mapping[str, Any], control: Mapping[str, Any]) -> float:
    """Distance uses only contemporaneously available matching characteristics."""
    score = 0.0
    winner_sector = str(winner.get("sector") or "").casefold().strip()
    control_sector = str(control.get("sector") or "").casefold().strip()
    if winner_sector and control_sector and winner_sector != control_sector:
        score += 5.0
    winner_cap = safe_float(winner.get("market_cap"))
    control_cap = safe_float(control.get("market_cap"))
    if winner_cap > 0 and control_cap > 0:
        score += abs(log1p(winner_cap) - log1p(control_cap))
    winner_price = safe_float(winner.get("close"))
    control_price = safe_float(control.get("close"))
    if winner_price > 0 and control_price > 0:
        score += abs(log1p(winner_price) - log1p(control_price))
    score += abs(
        safe_float(winner.get("realized_volatility_20d_pct"))
        - safe_float(control.get("realized_volatility_20d_pct"))
    )
    score += abs(
        safe_float(winner.get("return_20d_lag_pct"))
        - safe_float(control.get("return_20d_lag_pct"))
    ) / 10.0
    return score


def build_matched_study(
    rows: Sequence[Mapping[str, Any]], *, winner_return_pct: float = 5.0,
    maximum_control_return_pct: float = 1.0, controls_per_winner: int = 5,
    minimum_calendar_gap_days: int = 9,
) -> List[Dict[str, Any]]:
    if controls_per_winner <= 0:
        raise ValueError("controls_per_winner must be positive")
    if maximum_control_return_pct >= winner_return_pct:
        raise ValueError("control ceiling must be below winner threshold")
    rows_by_day: Dict[date, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_day[_day(row)].append(row)
    winners = select_non_overlapping_winners(
        rows, winner_return_pct=winner_return_pct,
        minimum_calendar_gap_days=minimum_calendar_gap_days,
    )
    output: List[Dict[str, Any]] = []
    for event_number, winner in enumerate(winners, 1):
        event_id = f"winner-{_day(winner).isoformat()}-{_symbol(winner)}-{event_number}"
        winner_copy = dict(winner)
        winner_copy.update({
            "study_event_id": event_id, "study_role": "winner", "study_label": 1,
            "winner_return_threshold_pct": winner_return_pct,
            "matched_winner_symbol": _symbol(winner), "match_distance": 0.0,
        })
        output.append(winner_copy)
        candidates = [
            row for row in rows_by_day[_day(winner)]
            if _symbol(row) != _symbol(winner)
            and safe_float(row.get("label_forward_return_5d_pct")) <= maximum_control_return_pct
        ]
        ranked = sorted(candidates, key=lambda row: (match_distance(winner, row), _symbol(row)))
        for control in ranked[:controls_per_winner]:
            control_copy = dict(control)
            control_copy.update({
                "study_event_id": event_id, "study_role": "control", "study_label": 0,
                "winner_return_threshold_pct": winner_return_pct,
                "matched_winner_symbol": _symbol(winner),
                "match_distance": round(match_distance(winner, control), 8),
            })
            output.append(control_copy)
    return output


def study_summary(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    winners = [row for row in rows if row.get("study_role") == "winner"]
    controls = [row for row in rows if row.get("study_role") == "control"]
    return {
        "winner_events": len(winners),
        "matched_controls": len(controls),
        "winner_symbols": len({_symbol(row) for row in winners}),
        "events_with_full_control_set": sum(
            1 for event_id in {str(row.get("study_event_id")) for row in winners}
            if sum(str(row.get("study_event_id")) == event_id for row in controls) >= 5
        ),
    }


def feature_contrasts(
    rows: Sequence[Mapping[str, Any]], features: Sequence[str] = DEFAULT_ANALYSIS_FEATURES,
) -> List[Dict[str, Any]]:
    """Compare only declared pre-event features; outcome fields are never inferred."""
    winners = [row for row in rows if row.get("study_role") == "winner"]
    controls = [row for row in rows if row.get("study_role") == "control"]
    contrasts: List[Dict[str, Any]] = []
    for feature in features:
        if feature.startswith("label_"):
            raise ValueError("outcome labels cannot be analyzed as pre-event features")
        winner_values = [safe_float(row.get(feature)) for row in winners if row.get(feature) is not None]
        control_values = [safe_float(row.get(feature)) for row in controls if row.get(feature) is not None]
        if not winner_values or not control_values:
            continue
        winner_mean = mean(winner_values)
        control_mean = mean(control_values)
        pooled_scale = ((pstdev(winner_values) ** 2 + pstdev(control_values) ** 2) / 2.0) ** 0.5
        contrasts.append({
            "feature": feature,
            "winner_mean": round(winner_mean, 8),
            "control_mean": round(control_mean, 8),
            "mean_difference": round(winner_mean - control_mean, 8),
            "standardized_mean_difference": round((winner_mean - control_mean) / pooled_scale, 8) if pooled_scale > 0 else 0.0,
            "winner_count": len(winner_values), "control_count": len(control_values),
        })
    return sorted(contrasts, key=lambda row: abs(row["standardized_mean_difference"]), reverse=True)
