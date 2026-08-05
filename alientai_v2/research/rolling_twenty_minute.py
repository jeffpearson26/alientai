from __future__ import annotations

"""Leakage-safe one-minute features and configurable intraday research labels."""

import math
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo


NEW_YORK = ZoneInfo("America/New_York")
REGULAR_OPEN = time(9, 30)
REGULAR_LAST_BAR = time(15, 59)
DEFAULT_HORIZON_MINUTES = 20
ALLOWED_HORIZON_MINUTES = (5, 10, 20, 30, 60, 90)
ROUND_TRIP_COST_PCT = 0.25
RETURN_WINDOWS = (1, 2, 5, 10, 20, 60)


@dataclass(frozen=True)
class MinuteCandle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def _timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        stamp = value
    else:
        stamp = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    if stamp.tzinfo is None:
        return stamp.replace(tzinfo=NEW_YORK)
    return stamp.astimezone(NEW_YORK)


def _candle(row: Mapping[str, Any]) -> MinuteCandle:
    stamp = _timestamp(row["timestamp"])
    values = tuple(float(row[field]) for field in ("open", "high", "low", "close"))
    volume = float(row["volume"])
    if stamp.second or stamp.microsecond:
        raise ValueError("one-minute candle timestamp must align to a minute")
    if min(values) <= 0 or volume < 0:
        raise ValueError("one-minute candle contains invalid price or volume")
    if values[1] < max(values[0], values[2], values[3]):
        raise ValueError("one-minute candle high is invalid")
    if values[2] > min(values[0], values[1], values[3]):
        raise ValueError("one-minute candle low is invalid")
    return MinuteCandle(stamp, *values, volume)


def regular_session(rows: Iterable[Mapping[str, Any]]) -> list[MinuteCandle]:
    candles = [
        _candle(row)
        for row in rows
        if REGULAR_OPEN <= _timestamp(row["timestamp"]).time() <= REGULAR_LAST_BAR
    ]
    candles.sort(key=lambda item: item.timestamp)
    if len({item.timestamp for item in candles}) != len(candles):
        raise ValueError("duplicate one-minute candle timestamp")
    dates = {item.timestamp.date() for item in candles}
    if len(dates) > 1:
        raise ValueError("regular_session accepts exactly one market date")
    return candles


def latest_completed_bar_start(captured_at: datetime) -> datetime:
    """Return the start of the latest fully completed one-minute interval."""
    stamp = captured_at
    if stamp.tzinfo is None:
        raise ValueError("captured_at must be timezone-aware")
    stamp = stamp.astimezone(NEW_YORK).replace(second=0, microsecond=0)
    return stamp - timedelta(minutes=1)


def _safe_return(new_value: float, old_value: float) -> float:
    return (new_value / old_value - 1.0) * 100.0


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _standard_deviation(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    average = _mean(values)
    return math.sqrt(sum((value - average) ** 2 for value in values) / len(values))


def build_features_at(
    rows: Iterable[Mapping[str, Any]],
    feature_bar_start: datetime,
) -> dict[str, Any] | None:
    candles = regular_session(rows)
    wanted = _timestamp(feature_bar_start)
    index_by_stamp = {item.timestamp: index for index, item in enumerate(candles)}
    index = index_by_stamp.get(wanted)
    if index is None:
        return None
    current = candles[index]
    session = candles[: index + 1]
    minute_of_session = int(
        (current.timestamp.replace(tzinfo=None) - datetime.combine(
            current.timestamp.date(), REGULAR_OPEN
        )).total_seconds()
        // 60
    )
    if minute_of_session < 0 or minute_of_session > 389:
        return None

    output: dict[str, Any] = {
        "feature_bar_start_et": current.timestamp.isoformat(),
        "effective_as_of_et": (current.timestamp + timedelta(minutes=1)).isoformat(),
        "minute_of_session": minute_of_session,
        "minute_sin": math.sin(2.0 * math.pi * minute_of_session / 390.0),
        "minute_cos": math.cos(2.0 * math.pi * minute_of_session / 390.0),
        "day_of_week": current.timestamp.weekday(),
        "session_return_pct": _safe_return(current.close, session[0].open),
        "session_distance_from_high_pct": _safe_return(
            current.close, max(item.high for item in session)
        ),
        "session_distance_from_low_pct": _safe_return(
            current.close, min(item.low for item in session)
        ),
        "feature_close": current.close,
    }
    cumulative_volume = sum(item.volume for item in session)
    if cumulative_volume > 0:
        vwap = sum(
            ((item.high + item.low + item.close) / 3.0) * item.volume
            for item in session
        ) / cumulative_volume
        output["distance_from_session_vwap_pct"] = _safe_return(current.close, vwap)
    else:
        output["distance_from_session_vwap_pct"] = None

    for window in RETURN_WINDOWS:
        available = (
            index >= window
            and current.timestamp - candles[index - window].timestamp
            == timedelta(minutes=window)
        )
        output[f"history_{window}m_available"] = available
        output[f"return_{window}m_pct"] = (
            _safe_return(current.close, candles[index - window].close)
            if available
            else None
        )

    recent_returns = [
        _safe_return(candles[position].close, candles[position - 1].close)
        for position in range(max(1, index - 19), index + 1)
    ]
    output["realized_volatility_20m_pct"] = _standard_deviation(recent_returns)

    for window in (5, 20, 60):
        start = max(0, index - window + 1)
        sample = candles[start : index + 1]
        complete = (
            len(sample) == window
            and sample[-1].timestamp - sample[0].timestamp
            == timedelta(minutes=window - 1)
        )
        output[f"volume_history_{window}m_available"] = complete
        average_volume = _mean([item.volume for item in sample])
        output[f"volume_vs_{window}m_mean"] = (
            current.volume / average_volume if average_volume > 0 else None
        )
        output[f"range_{window}m_pct"] = _safe_return(
            max(item.high for item in sample),
            min(item.low for item in sample),
        )
    return output


def build_label_at(
    rows: Iterable[Mapping[str, Any]],
    feature_bar_start: datetime,
    *,
    round_trip_cost_pct: float = ROUND_TRIP_COST_PCT,
    horizon_minutes: int = DEFAULT_HORIZON_MINUTES,
) -> dict[str, Any] | None:
    if round_trip_cost_pct < 0:
        raise ValueError("round_trip_cost_pct must be nonnegative")
    if horizon_minutes not in ALLOWED_HORIZON_MINUTES:
        raise ValueError(
            f"horizon_minutes must be one of {ALLOWED_HORIZON_MINUTES}"
        )
    candles = regular_session(rows)
    wanted = _timestamp(feature_bar_start)
    by_stamp = {item.timestamp: item for item in candles}
    if wanted not in by_stamp:
        return None
    future_stamps = [
        wanted + timedelta(minutes=offset)
        for offset in range(1, horizon_minutes + 1)
    ]
    if any(stamp.date() != wanted.date() or stamp not in by_stamp for stamp in future_stamps):
        return None
    entry = by_stamp[future_stamps[0]]
    target = by_stamp[future_stamps[-1]]
    gross = _safe_return(target.close, entry.open)
    return {
        "label_effective_as_of_et": (wanted + timedelta(minutes=1)).isoformat(),
        "label_entry_at_et": future_stamps[0].isoformat(),
        "label_target_at_et": (
            wanted + timedelta(minutes=horizon_minutes + 1)
        ).isoformat(),
        "label_entry_open": entry.open,
        "label_target_close": target.close,
        "label_forward_return_gross_pct": gross,
        "label_forward_return_net_pct": gross - round_trip_cost_pct,
        "label_positive_after_cost": gross > round_trip_cost_pct,
        "round_trip_cost_pct": round_trip_cost_pct,
        "entry_assumption": "next_minute_open",
        "horizon_minutes": horizon_minutes,
    }


def build_observation_at(
    rows: Iterable[Mapping[str, Any]],
    feature_bar_start: datetime,
    *,
    horizon_minutes: int = DEFAULT_HORIZON_MINUTES,
) -> dict[str, Any] | None:
    materialized = list(rows)
    features = build_features_at(materialized, feature_bar_start)
    label = build_label_at(
        materialized,
        feature_bar_start,
        horizon_minutes=horizon_minutes,
    )
    if features is None or label is None:
        return None
    return {
        **features,
        **label,
        "interval": "1min",
        "horizon_minutes": horizon_minutes,
        "research_only": True,
        "execution_enabled": False,
    }


def build_model_features_at(
    symbol_rows: Iterable[Mapping[str, Any]],
    qqq_rows: Iterable[Mapping[str, Any]],
    spy_rows: Iterable[Mapping[str, Any]],
    captured_at: datetime,
) -> dict[str, Any] | None:
    """Build the exact compiler feature vector for the newest completed minute."""

    if captured_at.tzinfo is None:
        raise ValueError("captured_at must be timezone-aware")
    import pandas as pd

    from compile_rolling_twenty_minute_panel import build_feature_frame, feature_names

    wanted = latest_completed_bar_start(captured_at)

    def frame(rows: Iterable[Mapping[str, Any]]) -> Any:
        output = pd.DataFrame(list(rows))
        if output.empty:
            return output
        output["timestamp"] = pd.to_datetime(output["timestamp"])
        if output["timestamp"].dt.tz is not None:
            output["timestamp"] = (
                output["timestamp"].dt.tz_convert(NEW_YORK).dt.tz_localize(None)
            )
        return output

    compiled = build_feature_frame(
        frame(symbol_rows),
        frame(qqq_rows),
        frame(spy_rows),
    )
    wanted_naive = wanted.replace(tzinfo=None)
    matched = compiled[compiled["timestamp"] == wanted_naive]
    if len(matched) != 1:
        return None
    row = matched.iloc[0]
    if pd.isna(row["qqq_session_return_pct"]) or pd.isna(
        row["spy_session_return_pct"]
    ):
        return None
    return {
        "feature_bar_start_et": wanted.isoformat(),
        "effective_as_of_et": (wanted + timedelta(minutes=1)).isoformat(),
        "feature_names": feature_names(),
        "features": {
            name: None if pd.isna(row[name]) else float(row[name])
            for name in feature_names()
        },
        "research_only": True,
        "execution_enabled": False,
    }
