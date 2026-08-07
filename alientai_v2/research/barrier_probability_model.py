from __future__ import annotations

"""Pure feature, label, and chronology logic for barrier probabilities."""

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


FEATURE_LOOKBACK = 60
FEATURE_NAMES = (
    "barrier_return_1d_pct",
    "barrier_return_3d_pct",
    "barrier_return_5d_pct",
    "barrier_return_10d_pct",
    "barrier_rsi_14",
    "barrier_stochastic_k_14",
    "barrier_cci_20",
    "barrier_atr_14_pct",
    "barrier_bollinger_pct_b_20",
    "barrier_bollinger_width_20_pct",
    "barrier_distance_ema_10_pct",
    "barrier_distance_ema_20_pct",
    "barrier_macd_histogram_pct",
    "barrier_adx_14",
    "barrier_relative_volume_20",
    "barrier_intraday_range_pct",
    "barrier_close_location",
    "barrier_realized_volatility_20d_pct",
    "barrier_volatility_ratio_5d_20d",
)

REQUIRED_ALPHA_FIELDS = (
    "1. open",
    "2. high",
    "3. low",
    "4. close",
    "5. adjusted close",
    "6. volume",
    "7. dividend amount",
    "8. split coefficient",
)


def _pct(current: float, prior: float) -> float:
    return (current / prior - 1.0) * 100.0


def _ema(values: np.ndarray, period: int) -> np.ndarray:
    if len(values) == 0:
        return np.asarray([], dtype=float)
    alpha = 2.0 / (period + 1.0)
    output = np.empty(len(values), dtype=float)
    output[0] = float(values[0])
    for index in range(1, len(values)):
        output[index] = (
            alpha * float(values[index])
            + (1.0 - alpha) * output[index - 1]
        )
    return output


def _rsi(values: np.ndarray, period: int) -> float:
    changes = np.diff(values)
    gains = np.maximum(changes, 0.0)
    losses = np.maximum(-changes, 0.0)
    average_gain = float(np.mean(gains[:period]))
    average_loss = float(np.mean(losses[:period]))
    for index in range(period, len(changes)):
        average_gain = (
            average_gain * (period - 1) + float(gains[index])
        ) / period
        average_loss = (
            average_loss * (period - 1) + float(losses[index])
        ) / period
    if average_loss == 0.0:
        return 100.0 if average_gain > 0.0 else 50.0
    return 100.0 - 100.0 / (1.0 + average_gain / average_loss)


def _true_ranges(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
) -> np.ndarray:
    return np.maximum.reduce(
        (
            highs[1:] - lows[1:],
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1]),
        )
    )


def _adx(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    period: int,
) -> float:
    up = np.diff(highs)
    down = -np.diff(lows)
    plus_dm = np.where((up > down) & (up > 0.0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0.0), down, 0.0)
    tr = _true_ranges(highs, lows, closes)
    atr = float(np.sum(tr[:period]))
    plus = float(np.sum(plus_dm[:period]))
    minus = float(np.sum(minus_dm[:period]))
    dx_values: list[float] = []
    for index in range(period, len(tr)):
        atr = atr - atr / period + float(tr[index])
        plus = plus - plus / period + float(plus_dm[index])
        minus = minus - minus / period + float(minus_dm[index])
        if atr <= 0.0:
            continue
        plus_di = 100.0 * plus / atr
        minus_di = 100.0 * minus / atr
        denominator = plus_di + minus_di
        dx_values.append(
            0.0
            if denominator <= 0.0
            else 100.0 * abs(plus_di - minus_di) / denominator
        )
    if len(dx_values) < period:
        raise ValueError("insufficient candles for ADX")
    adx = float(np.mean(dx_values[:period]))
    for value in dx_values[period:]:
        adx = (adx * (period - 1) + float(value)) / period
    return adx


def technical_features(
    candles: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    """Compute features from a bounded window ending at the decision close."""
    if len(candles) < FEATURE_LOOKBACK:
        raise ValueError(
            f"barrier features require {FEATURE_LOOKBACK} completed candles"
        )
    window = candles[-FEATURE_LOOKBACK:]
    closes = np.asarray([float(row["close"]) for row in window], dtype=float)
    opens = np.asarray([float(row["open"]) for row in window], dtype=float)
    highs = np.asarray([float(row["high"]) for row in window], dtype=float)
    lows = np.asarray([float(row["low"]) for row in window], dtype=float)
    volumes = np.asarray([float(row["volume"]) for row in window], dtype=float)
    envelope_scale = np.maximum.reduce(
        (np.ones(len(closes)), opens, highs, lows, closes)
    )
    envelope_tolerance = envelope_scale * 1e-12
    if (
        np.any(closes <= 0.0)
        or np.any(opens <= 0.0)
        or np.any(highs <= 0.0)
        or np.any(lows <= 0.0)
        or np.any(volumes < 0.0)
        or np.any(
            highs + envelope_tolerance
            < np.maximum.reduce((opens, lows, closes))
        )
        or np.any(
            lows - envelope_tolerance
            > np.minimum.reduce((opens, highs, closes))
        )
    ):
        raise ValueError("invalid adjusted OHLCV input")

    changes = np.diff(np.log(closes))
    true_ranges = _true_ranges(highs, lows, closes)
    atr = float(np.mean(true_ranges[-14:]))
    typical = (highs[-20:] + lows[-20:] + closes[-20:]) / 3.0
    typical_mean = float(np.mean(typical))
    mean_deviation = float(np.mean(np.abs(typical - typical_mean)))
    cci = (
        0.0
        if mean_deviation <= 0.0
        else float((typical[-1] - typical_mean) / (0.015 * mean_deviation))
    )

    middle = float(np.mean(closes[-20:]))
    deviation = float(np.std(closes[-20:], ddof=0))
    lower_band = middle - 2.0 * deviation
    upper_band = middle + 2.0 * deviation
    band_range = upper_band - lower_band

    highest_14 = float(np.max(highs[-14:]))
    lowest_14 = float(np.min(lows[-14:]))
    stochastic = (
        50.0
        if highest_14 <= lowest_14
        else float(
            (closes[-1] - lowest_14)
            / (highest_14 - lowest_14)
            * 100.0
        )
    )

    ema_10 = _ema(closes, 10)
    ema_20 = _ema(closes, 20)
    macd = _ema(closes, 12) - _ema(closes, 26)
    macd_signal = _ema(macd, 9)
    prior_volume = float(np.mean(volumes[-21:-1]))
    daily_range = float(highs[-1] - lows[-1])
    vol_20 = float(np.std(changes[-20:], ddof=0))
    vol_5 = float(np.std(changes[-5:], ddof=0))

    output = {
        "barrier_return_1d_pct": _pct(closes[-1], closes[-2]),
        "barrier_return_3d_pct": _pct(closes[-1], closes[-4]),
        "barrier_return_5d_pct": _pct(closes[-1], closes[-6]),
        "barrier_return_10d_pct": _pct(closes[-1], closes[-11]),
        "barrier_rsi_14": _rsi(closes[-40:], 14),
        "barrier_stochastic_k_14": stochastic,
        "barrier_cci_20": cci,
        "barrier_atr_14_pct": atr / closes[-1] * 100.0,
        "barrier_bollinger_pct_b_20": (
            0.5
            if band_range <= 0.0
            else (closes[-1] - lower_band) / band_range
        ),
        "barrier_bollinger_width_20_pct": (
            0.0 if middle <= 0.0 else band_range / middle * 100.0
        ),
        "barrier_distance_ema_10_pct": _pct(closes[-1], ema_10[-1]),
        "barrier_distance_ema_20_pct": _pct(closes[-1], ema_20[-1]),
        "barrier_macd_histogram_pct": (
            (macd[-1] - macd_signal[-1]) / closes[-1] * 100.0
        ),
        "barrier_adx_14": _adx(highs, lows, closes, 14),
        "barrier_relative_volume_20": (
            0.0 if prior_volume <= 0.0 else volumes[-1] / prior_volume
        ),
        "barrier_intraday_range_pct": daily_range / closes[-1] * 100.0,
        "barrier_close_location": (
            0.5 if daily_range <= 0.0 else (closes[-1] - lows[-1]) / daily_range
        ),
        "barrier_realized_volatility_20d_pct": (
            vol_20 * math.sqrt(252.0) * 100.0
        ),
        "barrier_volatility_ratio_5d_20d": (
            1.0 if vol_20 <= 0.0 else vol_5 / vol_20
        ),
    }
    if set(output) != set(FEATURE_NAMES):
        raise AssertionError("feature contract mismatch")
    if any(not math.isfinite(float(value)) for value in output.values()):
        raise ValueError("non-finite barrier feature")
    return {name: float(output[name]) for name in FEATURE_NAMES}


def adjusted_daily_candles(
    path: Path,
    expected_symbol: str,
) -> list[dict[str, Any]]:
    """Load same-row adjusted OHLC and unadjusted point-in-time volume."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    metadata = payload.get("Meta Data") or {}
    actual_symbol = str(metadata.get("2. Symbol") or "").upper()
    if actual_symbol != expected_symbol.upper():
        raise ValueError(
            f"{path}: payload symbol {actual_symbol!r}; "
            f"expected {expected_symbol!r}"
        )
    series_matches = [
        value
        for key, value in payload.items()
        if str(key).startswith("Time Series") and isinstance(value, dict)
    ]
    if len(series_matches) != 1 or not series_matches[0]:
        raise ValueError(f"{path}: one nonempty time series is required")

    candles: list[dict[str, Any]] = []
    for market_date, row in sorted(series_matches[0].items()):
        if not isinstance(row, dict) or any(
            field not in row for field in REQUIRED_ALPHA_FIELDS
        ):
            raise ValueError(f"{path}: invalid row on {market_date}")
        values = {
            field: float(row[field])
            for field in REQUIRED_ALPHA_FIELDS
        }
        if any(not math.isfinite(value) for value in values.values()):
            raise ValueError(f"{path}: non-finite row on {market_date}")
        raw_open = values["1. open"]
        raw_high = values["2. high"]
        raw_low = values["3. low"]
        raw_close = values["4. close"]
        adjusted_close = values["5. adjusted close"]
        if (
            min(raw_open, raw_high, raw_low, raw_close, adjusted_close) <= 0.0
            or values["6. volume"] < 0.0
            or values["7. dividend amount"] < 0.0
            or values["8. split coefficient"] <= 0.0
            or raw_high < max(raw_open, raw_low, raw_close)
            or raw_low > min(raw_open, raw_high, raw_close)
        ):
            raise ValueError(f"{path}: invalid OHLC envelope on {market_date}")
        factor = adjusted_close / raw_close
        candles.append(
            {
                "market_date": str(market_date),
                "open": raw_open * factor,
                "high": raw_high * factor,
                "low": raw_low * factor,
                "close": adjusted_close,
                "volume": values["6. volume"],
                "dividend_amount": values["7. dividend amount"],
                "split_coefficient": values["8. split coefficient"],
            }
        )
    if len(candles) != len({row["market_date"] for row in candles}):
        raise ValueError(f"{path}: duplicate market dates")
    return candles


def resolve_barrier(
    candles: Sequence[Mapping[str, Any]],
    decision_index: int,
    *,
    upper_pct: float,
    lower_pct: float,
    horizon_sessions: int,
) -> dict[str, Any]:
    """Resolve daily first passage and preserve same-session uncertainty."""
    if upper_pct <= 0.0 or lower_pct <= 0.0:
        raise ValueError("barriers must be positive")
    if horizon_sessions < 1:
        raise ValueError("horizon must be positive")
    entry_index = decision_index + 1
    if decision_index < 0 or entry_index >= len(candles):
        return {"outcome_status": "incomplete_no_entry"}
    entry_price = float(candles[entry_index]["open"])
    if entry_price <= 0.0:
        raise ValueError("entry price must be positive")
    upper_price = entry_price * (1.0 + upper_pct)
    lower_price = entry_price * (1.0 - lower_pct)
    final_required_index = entry_index + horizon_sessions - 1
    final_available_index = min(final_required_index, len(candles) - 1)

    for index in range(entry_index, final_available_index + 1):
        high = float(candles[index]["high"])
        low = float(candles[index]["low"])
        hit_upper = high >= upper_price
        hit_lower = low <= lower_price
        if not hit_upper and not hit_lower:
            continue
        if hit_upper and hit_lower:
            status = "ambiguous_same_session"
            lower_label, upper_label, conditional_label = 0, 1, None
        elif hit_upper:
            status = "definite_upper_first"
            lower_label = upper_label = conditional_label = 1
        else:
            status = "definite_lower_first"
            lower_label = upper_label = conditional_label = 0
        return {
            "outcome_status": status,
            "entry_market_date": str(candles[entry_index]["market_date"]),
            "entry_price": entry_price,
            "upper_barrier_price": upper_price,
            "lower_barrier_price": lower_price,
            "label_information_end_date": str(
                candles[index]["market_date"]
            ),
            "label_resolution_session": index - entry_index + 1,
            "label_lower_bound": lower_label,
            "label_upper_bound": upper_label,
            "label_conditional_unambiguous": conditional_label,
        }

    if final_required_index >= len(candles):
        return {
            "outcome_status": "incomplete_unresolved",
            "entry_market_date": str(candles[entry_index]["market_date"]),
            "entry_price": entry_price,
            "upper_barrier_price": upper_price,
            "lower_barrier_price": lower_price,
        }
    return {
        "outcome_status": "timeout_failure",
        "entry_market_date": str(candles[entry_index]["market_date"]),
        "entry_price": entry_price,
        "upper_barrier_price": upper_price,
        "lower_barrier_price": lower_price,
        "label_information_end_date": str(
            candles[final_required_index]["market_date"]
        ),
        "label_resolution_session": horizon_sessions,
        "label_lower_bound": 0,
        "label_upper_bound": 0,
        "label_conditional_unambiguous": 0,
    }


def chronological_date_sets(
    dates: Sequence[str],
    *,
    embargo_sessions: int,
) -> dict[str, set[str]]:
    """Freeze five whole-date stages with two-sided development embargoes."""
    ordered = sorted(set(str(value) for value in dates))
    if len(ordered) < 400:
        raise ValueError("at least 400 decision dates are required")
    boundaries = [
        int(len(ordered) * fraction)
        for fraction in (0.50, 0.65, 0.75, 0.85)
    ]
    train_end, fit_end, calibration_end, policy_end = boundaries

    def middle(left: int, right: int) -> set[str]:
        start = left + (embargo_sessions if left else 0)
        end = right - embargo_sessions
        if end <= start:
            raise ValueError("insufficient dates after embargo")
        return set(ordered[start:end])

    stages = {
        "train": middle(0, train_end),
        "fit_validation": middle(train_end, fit_end),
        "calibration": middle(fit_end, calibration_end),
        "policy_validation": middle(calibration_end, policy_end),
        "sealed_test": set(ordered[policy_end + embargo_sessions :]),
    }
    stages["embargo"] = set(ordered) - set().union(*stages.values())
    if any(not dates for dates in stages.values()):
        raise ValueError("every stage, including embargo, must be nonempty")
    return stages


def project_probability_bounds(
    lower: np.ndarray,
    upper: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Project independently calibrated bounds to a coherent interval."""
    if lower.shape != upper.shape:
        raise ValueError("probability arrays must have equal shape")
    lower = np.clip(lower.astype(float), 0.0, 1.0)
    upper = np.clip(upper.astype(float), 0.0, 1.0)
    crossed = lower > upper
    return np.minimum(lower, upper), np.maximum(lower, upper), crossed
