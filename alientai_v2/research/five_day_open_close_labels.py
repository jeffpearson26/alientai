"""Leakage-safe next-open to fifth-close labels for five-day research."""

from __future__ import annotations

from datetime import date
import math
from typing import Any, Iterable, Mapping


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) and result > 0.0 else None


def _day(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def build_next_open_five_close_labels(
    symbol: str,
    candles: Iterable[Mapping[str, Any]],
    *,
    round_trip_cost_pct: float = 0.25,
    large_move_target_pct: float = 2.0,
    maximum_calendar_gap_days: int = 5,
) -> list[dict[str, Any]]:
    return build_next_open_horizon_close_labels(
        symbol,
        candles,
        horizon_sessions=5,
        round_trip_cost_pct=round_trip_cost_pct,
        large_move_target_pct=large_move_target_pct,
        maximum_calendar_gap_days=maximum_calendar_gap_days,
    )


def build_next_open_horizon_close_labels(
    symbol: str,
    candles: Iterable[Mapping[str, Any]],
    *,
    horizon_sessions: int,
    round_trip_cost_pct: float = 0.25,
    large_move_target_pct: float = 2.0,
    maximum_calendar_gap_days: int = 5,
) -> list[dict[str, Any]]:
    """Create labels known only after the requested number of sessions.

    The decision is made after a daily candle closes. Entry is the next
    session's open. That entry session is session one. Invalid or discontinuous
    windows are excluded rather than labeled as losses.
    """
    normalized_symbol = str(symbol or "").upper().strip()
    if not normalized_symbol:
        raise ValueError("symbol is required")
    if not math.isfinite(round_trip_cost_pct) or round_trip_cost_pct < 0:
        raise ValueError("round_trip_cost_pct must be finite and non-negative")
    if not math.isfinite(large_move_target_pct):
        raise ValueError("large_move_target_pct must be finite")
    if maximum_calendar_gap_days < 1:
        raise ValueError("maximum_calendar_gap_days must be positive")
    if horizon_sessions < 2:
        raise ValueError("horizon_sessions must be at least two")

    source = list(candles)
    parsed_days = [_day(row.get("date")) for row in source]
    if any(day is None for day in parsed_days):
        raise ValueError("every candle must have an ISO date")
    days = [day for day in parsed_days if day is not None]
    if any(days[index] <= days[index - 1] for index in range(1, len(days))):
        raise ValueError("candle dates must be unique and strictly increasing")

    results: list[dict[str, Any]] = []
    for decision_index in range(max(0, len(source) - horizon_sessions)):
        exit_index = decision_index + horizon_sessions
        window_days = days[decision_index:exit_index + 1]
        if any(
            (window_days[index] - window_days[index - 1]).days > maximum_calendar_gap_days
            for index in range(1, len(window_days))
        ):
            continue

        entry_open = _number(source[decision_index + 1].get("open"))
        exit_close = _number(source[exit_index].get("close"))
        if entry_open is None or exit_close is None:
            continue
        gross_return_pct = (exit_close / entry_open - 1.0) * 100.0
        net_return_pct = gross_return_pct - round_trip_cost_pct
        results.append({
            "symbol": normalized_symbol,
            "decision_date": days[decision_index].isoformat(),
            "entry_date": days[decision_index + 1].isoformat(),
            "exit_date": days[exit_index].isoformat(),
            "entry_price": entry_open,
            "exit_price": exit_close,
            "holding_sessions": horizon_sessions,
            "entry_assumption": "next_regular_session_open",
            "exit_assumption": f"{horizon_sessions}th_regular_session_close",
            "round_trip_cost_pct": float(round_trip_cost_pct),
            "gross_return_pct": gross_return_pct,
            "net_return_pct": net_return_pct,
            "label_positive_net_return": int(net_return_pct > 0.0),
            "label_large_move": int(net_return_pct >= large_move_target_pct),
            "large_move_target_pct": float(large_move_target_pct),
        })
    return results
