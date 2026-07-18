from __future__ import annotations

"""Point-in-time daily technical snapshot for retrospective winner studies."""

from statistics import mean, pstdev
from typing import Any, Dict, Mapping, Sequence

from alientai_v2.features.insider_purchase_features import safe_float


def _ema(values: Sequence[float], period: int) -> float:
    if not values:
        return 0.0
    alpha = 2.0 / (period + 1.0)
    result = values[0]
    for value in values[1:]:
        result = alpha * value + (1.0 - alpha) * result
    return result


def _ema_series(values: Sequence[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    output = [values[0]]
    for value in values[1:]:
        output.append(alpha * value + (1.0 - alpha) * output[-1])
    return output


def _rsi(closes: Sequence[float], period: int) -> float:
    if len(closes) <= period:
        return 50.0
    changes = [closes[index] - closes[index - 1] for index in range(len(closes) - period, len(closes))]
    gains = mean(max(change, 0.0) for change in changes)
    losses = mean(max(-change, 0.0) for change in changes)
    if losses == 0:
        return 100.0 if gains > 0 else 50.0
    return 100.0 - (100.0 / (1.0 + gains / losses))


def build_technical_snapshot(candles: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if len(candles) < 60:
        raise ValueError("technical snapshot requires at least 60 chronological candles")
    closes = [safe_float(row.get("close")) for row in candles]
    highs = [safe_float(row.get("high"), closes[index]) or closes[index] for index, row in enumerate(candles)]
    lows = [safe_float(row.get("low"), closes[index]) or closes[index] for index, row in enumerate(candles)]
    volumes = [max(0.0, safe_float(row.get("volume"))) for row in candles]
    if any(close <= 0 for close in closes):
        raise ValueError("technical snapshot requires positive closes")

    returns = [((closes[index] / closes[index - 1]) - 1.0) * 100.0 for index in range(1, len(closes))]
    ema9, ema21, ema50 = (_ema(closes, period) for period in (9, 21, 50))
    ema12_series = _ema_series(closes, 12)
    ema26_series = _ema_series(closes, 26)
    macd_series = [fast - slow for fast, slow in zip(ema12_series, ema26_series)]
    macd_signal = _ema(macd_series, 9)
    true_ranges = []
    plus_dm = []
    minus_dm = []
    for index in range(1, len(candles)):
        true_ranges.append(max(highs[index] - lows[index], abs(highs[index] - closes[index - 1]), abs(lows[index] - closes[index - 1])))
        up_move = highs[index] - highs[index - 1]
        down_move = lows[index - 1] - lows[index]
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
    atr14 = mean(true_ranges[-14:])
    plus_di = 100.0 * mean(plus_dm[-14:]) / atr14 if atr14 > 0 else 0.0
    minus_di = 100.0 * mean(minus_dm[-14:]) / atr14 if atr14 > 0 else 0.0
    adx14 = 100.0 * abs(plus_di - minus_di) / (plus_di + minus_di) if plus_di + minus_di > 0 else 0.0

    middle = mean(closes[-20:])
    band_std = pstdev(closes[-20:])
    upper, lower = middle + 2 * band_std, middle - 2 * band_std
    volume10 = mean(volumes[-10:])
    volume20 = mean(volumes[-20:])
    obv = 0.0
    obv_ten_days_ago = 0.0
    for index in range(1, len(closes)):
        if index == len(closes) - 10:
            obv_ten_days_ago = obv
        obv += volumes[index] if closes[index] > closes[index - 1] else -volumes[index] if closes[index] < closes[index - 1] else 0.0
    ten_day_returns = returns[-10:]
    prior_twenty_volatility = pstdev(returns[-30:-10]) if len(returns) >= 30 else 0.0
    recent_five_volatility = pstdev(returns[-5:])

    return {
        "technical_rsi_2": round(_rsi(closes, 2), 6),
        "technical_rsi_14": round(_rsi(closes, 14), 6),
        "technical_ema9_distance_pct": round((closes[-1] / ema9 - 1.0) * 100.0, 6),
        "technical_ema21_distance_pct": round((closes[-1] / ema21 - 1.0) * 100.0, 6),
        "technical_ema50_distance_pct": round((closes[-1] / ema50 - 1.0) * 100.0, 6),
        "technical_ema_bullish_alignment": ema9 > ema21 > ema50,
        "technical_macd_pct": round(macd_series[-1] / closes[-1] * 100.0, 6),
        "technical_macd_signal_pct": round(macd_signal / closes[-1] * 100.0, 6),
        "technical_macd_histogram_pct": round((macd_series[-1] - macd_signal) / closes[-1] * 100.0, 6),
        "technical_atr14_pct": round(atr14 / closes[-1] * 100.0, 6),
        "technical_adx14": round(adx14, 6),
        "technical_plus_di14": round(plus_di, 6),
        "technical_minus_di14": round(minus_di, 6),
        "technical_bollinger_width_pct": round((upper - lower) / middle * 100.0, 6) if middle > 0 else 0.0,
        "technical_bollinger_position": round((closes[-1] - lower) / (upper - lower), 6) if upper > lower else 0.5,
        "technical_relative_volume_10_vs_20": round(volume10 / volume20, 6) if volume20 > 0 else 0.0,
        "technical_latest_relative_volume_20": round(volumes[-1] / volume20, 6) if volume20 > 0 else 0.0,
        "technical_obv_change_10d_normalized": round((obv - obv_ten_days_ago) / max(volume20, 1.0), 6),
        "technical_positive_days_10d": sum(value > 0 for value in ten_day_returns),
        "technical_max_daily_return_10d_pct": round(max(ten_day_returns), 6),
        "technical_min_daily_return_10d_pct": round(min(ten_day_returns), 6),
        "technical_volatility_compression_ratio": round(recent_five_volatility / prior_twenty_volatility, 6) if prior_twenty_volatility > 0 else 0.0,
    }
