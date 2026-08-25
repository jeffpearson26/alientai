from __future__ import annotations

"""Pure feature, setup, label, calibration, and metric logic for AI/semi H05 V1."""

import math
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping, Sequence

import numpy as np

from build_nasdaq_qqq_spy_60session_panel import load_adjusted_daily


FEATURE_NAMES = [
    "return_1d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "return_10d_pct",
    "return_20d_pct",
    "ema20_distance_pct",
    "ema50_distance_pct",
    "ema20_minus_ema50_pct",
    "ema20_slope_5d_pct",
    "ema50_slope_10d_pct",
    "range_position_20",
    "distance_from_20d_high_pct",
    "rsi14",
    "rsi14_change_5d",
    "macd_histogram_pct",
    "macd_histogram_change_5d_pct",
    "momentum_acceleration_5_vs20",
    "relative_volume_20",
    "volume_ratio_5_vs20",
    "up_down_volume_ratio_20",
    "pullback_volume_ratio_3_vs_prior10",
    "atr14_pct",
    "atr_contraction_5_vs20",
    "range_compression_5_vs20",
    "realized_volatility_10d_pct",
    "realized_volatility_20d_pct",
    "intraday_range_pct",
    "gap_pct",
    "close_location",
    "qqq_return_1d_pct",
    "qqq_return_5d_pct",
    "qqq_return_20d_pct",
    "soxx_return_1d_pct",
    "soxx_return_5d_pct",
    "soxx_return_20d_pct",
    "spy_return_1d_pct",
    "spy_return_5d_pct",
    "spy_return_20d_pct",
    "vixy_proxy_return_1d_pct",
    "vixy_proxy_return_5d_pct",
    "stock_minus_soxx_5d_pct",
    "stock_minus_soxx_20d_pct",
    "stock_minus_qqq_5d_pct",
    "stock_minus_qqq_20d_pct",
    "relative_strength_acceleration_soxx",
    "relative_strength_acceleration_qqq",
    "universe_above_20dma_fraction",
    "universe_green_fraction",
    "universe_median_return_1d_pct",
]

ENGINE_NAMES = (
    "PULLBACK_CONTINUATION_V1",
    "BREAKOUT_ANTICIPATION_V1",
    "SECTOR_RIP_MOMENTUM_V1",
)


def load_rows(path: Path) -> list[dict[str, Any]]:
    """Load audited adjusted daily rows with the panel's canonical date key."""
    return [{**row, "date": str(row["market_date"])} for row in load_adjusted_daily(path)]


def _pct(current: float, prior: float) -> float:
    if prior <= 0:
        raise ValueError("percentage denominator must be positive")
    return (current / prior - 1.0) * 100.0


def _ema(values: Sequence[float], span: int) -> np.ndarray:
    output = np.empty(len(values), dtype=np.float64)
    output[0] = float(values[0])
    alpha = 2.0 / (span + 1.0)
    for index in range(1, len(values)):
        output[index] = alpha * float(values[index]) + (1.0 - alpha) * output[index - 1]
    return output


def _rsi(values: Sequence[float], period: int = 14) -> float:
    if len(values) < period + 1:
        raise ValueError("insufficient RSI history")
    differences = np.diff(np.asarray(values, dtype=np.float64))
    gains = np.clip(differences[-period:], 0.0, None)
    losses = np.clip(-differences[-period:], 0.0, None)
    average_gain = float(np.mean(gains))
    average_loss = float(np.mean(losses))
    if average_loss <= 1e-15:
        return 100.0 if average_gain > 0 else 50.0
    return 100.0 - 100.0 / (1.0 + average_gain / average_loss)


def _true_ranges(rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    values = []
    for index, row in enumerate(rows):
        high = float(row["high"])
        low = float(row["low"])
        if index == 0:
            values.append(high - low)
            continue
        prior_close = float(rows[index - 1]["close"])
        values.append(max(high - low, abs(high - prior_close), abs(low - prior_close)))
    return np.asarray(values, dtype=np.float64)


def _annualized_realized_volatility(closes: Sequence[float], sessions: int) -> float:
    values = np.asarray(closes[-(sessions + 1) :], dtype=np.float64)
    returns = np.diff(np.log(values))
    return float(np.std(returns, ddof=1) * math.sqrt(252.0) * 100.0) if len(returns) >= 2 else 0.0


def _context_returns(rows: Sequence[Mapping[str, Any]]) -> tuple[float, float, float]:
    closes = [float(row["close"]) for row in rows]
    return _pct(closes[-1], closes[-2]), _pct(closes[-1], closes[-6]), _pct(closes[-1], closes[-21])


def build_feature_values(
    stock_rows: Sequence[Mapping[str, Any]],
    context_rows: Mapping[str, Sequence[Mapping[str, Any]]],
    breadth: Mapping[str, float],
) -> dict[str, float]:
    if len(stock_rows) < 61 or any(len(context_rows[name]) < 61 for name in ("QQQ", "SOXX", "SPY", "VIXY")):
        raise ValueError("features require 61 completed sessions")
    closes = np.asarray([float(row["close"]) for row in stock_rows], dtype=np.float64)
    highs = np.asarray([float(row["high"]) for row in stock_rows], dtype=np.float64)
    lows = np.asarray([float(row["low"]) for row in stock_rows], dtype=np.float64)
    opens = np.asarray([float(row["open"]) for row in stock_rows], dtype=np.float64)
    volumes = np.asarray([float(row["volume"]) for row in stock_rows], dtype=np.float64)
    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd = ema12 - ema26
    signal = _ema(macd, 9)
    histogram = macd - signal
    true_ranges = _true_ranges(stock_rows)
    high20 = float(np.max(highs[-20:]))
    low20 = float(np.min(lows[-20:]))
    range20 = high20 - low20
    daily_ranges = np.divide(highs - lows, closes, out=np.zeros_like(closes), where=closes > 0) * 100.0
    daily_returns = np.diff(closes) / closes[:-1]
    up_volume = float(np.sum(volumes[-20:][daily_returns[-20:] > 0]))
    down_volume = float(np.sum(volumes[-20:][daily_returns[-20:] < 0]))
    qqq1, qqq5, qqq20 = _context_returns(context_rows["QQQ"])
    soxx1, soxx5, soxx20 = _context_returns(context_rows["SOXX"])
    spy1, spy5, spy20 = _context_returns(context_rows["SPY"])
    vixy_closes = [float(row["close"]) for row in context_rows["VIXY"]]
    ret1 = _pct(closes[-1], closes[-2])
    ret3 = _pct(closes[-1], closes[-4])
    ret5 = _pct(closes[-1], closes[-6])
    ret10 = _pct(closes[-1], closes[-11])
    ret20 = _pct(closes[-1], closes[-21])
    stock_soxx5 = ret5 - soxx5
    stock_soxx20 = ret20 - soxx20
    stock_qqq5 = ret5 - qqq5
    stock_qqq20 = ret20 - qqq20
    result = {
        "return_1d_pct": ret1,
        "return_3d_pct": ret3,
        "return_5d_pct": ret5,
        "return_10d_pct": ret10,
        "return_20d_pct": ret20,
        "ema20_distance_pct": _pct(closes[-1], ema20[-1]),
        "ema50_distance_pct": _pct(closes[-1], ema50[-1]),
        "ema20_minus_ema50_pct": _pct(ema20[-1], ema50[-1]),
        "ema20_slope_5d_pct": _pct(ema20[-1], ema20[-6]),
        "ema50_slope_10d_pct": _pct(ema50[-1], ema50[-11]),
        "range_position_20": (float(closes[-1]) - low20) / range20 if range20 > 0 else 0.5,
        "distance_from_20d_high_pct": _pct(closes[-1], high20),
        "rsi14": _rsi(closes, 14),
        "rsi14_change_5d": _rsi(closes, 14) - _rsi(closes[:-5], 14),
        "macd_histogram_pct": float(histogram[-1] / closes[-1] * 100.0),
        "macd_histogram_change_5d_pct": float((histogram[-1] - histogram[-6]) / closes[-1] * 100.0),
        "momentum_acceleration_5_vs20": ret5 - ret20 / 4.0,
        "relative_volume_20": float(volumes[-1] / np.mean(volumes[-20:])) if np.mean(volumes[-20:]) > 0 else 0.0,
        "volume_ratio_5_vs20": float(np.mean(volumes[-5:]) / np.mean(volumes[-20:])) if np.mean(volumes[-20:]) > 0 else 0.0,
        "up_down_volume_ratio_20": up_volume / max(down_volume, 1.0),
        "pullback_volume_ratio_3_vs_prior10": float(np.mean(volumes[-3:]) / np.mean(volumes[-13:-3])) if np.mean(volumes[-13:-3]) > 0 else 0.0,
        "atr14_pct": float(np.mean(true_ranges[-14:]) / closes[-1] * 100.0),
        "atr_contraction_5_vs20": float(np.mean(true_ranges[-5:]) / np.mean(true_ranges[-20:])) if np.mean(true_ranges[-20:]) > 0 else 0.0,
        "range_compression_5_vs20": float(np.mean(daily_ranges[-5:]) / np.mean(daily_ranges[-20:])) if np.mean(daily_ranges[-20:]) > 0 else 0.0,
        "realized_volatility_10d_pct": _annualized_realized_volatility(closes, 10),
        "realized_volatility_20d_pct": _annualized_realized_volatility(closes, 20),
        "intraday_range_pct": float(daily_ranges[-1]),
        "gap_pct": _pct(opens[-1], closes[-2]),
        "close_location": (float(closes[-1]) - float(lows[-1])) / (float(highs[-1]) - float(lows[-1])) if highs[-1] > lows[-1] else 0.5,
        "qqq_return_1d_pct": qqq1,
        "qqq_return_5d_pct": qqq5,
        "qqq_return_20d_pct": qqq20,
        "soxx_return_1d_pct": soxx1,
        "soxx_return_5d_pct": soxx5,
        "soxx_return_20d_pct": soxx20,
        "spy_return_1d_pct": spy1,
        "spy_return_5d_pct": spy5,
        "spy_return_20d_pct": spy20,
        "vixy_proxy_return_1d_pct": _pct(vixy_closes[-1], vixy_closes[-2]),
        "vixy_proxy_return_5d_pct": _pct(vixy_closes[-1], vixy_closes[-6]),
        "stock_minus_soxx_5d_pct": stock_soxx5,
        "stock_minus_soxx_20d_pct": stock_soxx20,
        "stock_minus_qqq_5d_pct": stock_qqq5,
        "stock_minus_qqq_20d_pct": stock_qqq20,
        "relative_strength_acceleration_soxx": stock_soxx5 - stock_soxx20 / 4.0,
        "relative_strength_acceleration_qqq": stock_qqq5 - stock_qqq20 / 4.0,
        "universe_above_20dma_fraction": float(breadth["above_20dma_fraction"]),
        "universe_green_fraction": float(breadth["green_fraction"]),
        "universe_median_return_1d_pct": float(breadth["median_return_1d_pct"]),
    }
    if list(result) != FEATURE_NAMES:
        raise ValueError("feature order changed")
    if not all(math.isfinite(float(value)) for value in result.values()):
        raise ValueError("non-finite feature")
    return result


def detect_setups(features: Mapping[str, float]) -> dict[str, bool]:
    pullback = (
        features["ema20_distance_pct"] > 0.0
        and features["ema50_distance_pct"] > 0.0
        and features["ema20_minus_ema50_pct"] > 0.0
        and features["ema20_slope_5d_pct"] > 0.0
        and features["stock_minus_soxx_20d_pct"] > 0.0
        and -6.0 <= features["return_3d_pct"] <= 0.5
        and features["pullback_volume_ratio_3_vs_prior10"] <= 1.05
        and features["distance_from_20d_high_pct"] >= -10.0
    )
    breakout = (
        features["ema20_distance_pct"] > 0.0
        and features["range_position_20"] >= 0.70
        and features["distance_from_20d_high_pct"] >= -4.0
        and features["range_compression_5_vs20"] <= 0.85
        and features["atr_contraction_5_vs20"] <= 0.95
        and features["relative_strength_acceleration_soxx"] > 0.0
    )
    sector_rip = (
        features["soxx_return_1d_pct"] >= 0.75
        and features["qqq_return_1d_pct"] > 0.0
        and features["universe_green_fraction"] >= 0.70
        and features["universe_above_20dma_fraction"] >= 0.60
        and features["vixy_proxy_return_1d_pct"] <= 5.0
        and features["return_1d_pct"] > 0.0
        and features["stock_minus_soxx_5d_pct"] >= -2.0
    )
    return {
        "PULLBACK_CONTINUATION_V1": pullback,
        "BREAKOUT_ANTICIPATION_V1": breakout,
        "SECTOR_RIP_MOMENTUM_V1": sector_rip,
    }


def resolve_path_label(
    path_rows: Sequence[Mapping[str, Any]],
    *,
    entry_open: float,
    target_pct: float,
    stop_pct: float,
    cost_pct: float,
) -> dict[str, Any]:
    if len(path_rows) != 5 or entry_open <= 0:
        raise ValueError("path label requires five sessions and positive entry")
    target_price = entry_open * (1.0 + target_pct / 100.0)
    stop_price = entry_open * (1.0 - stop_pct / 100.0)
    outcome = "TIMEOUT"
    exit_price = float(path_rows[-1]["close"])
    event_date = str(path_rows[-1]["date"])
    sessions_to_event = 5
    for index, row in enumerate(path_rows, start=1):
        target_hit = float(row["high"]) >= target_price - 1e-12
        stop_hit = float(row["low"]) <= stop_price + 1e-12
        if stop_hit:
            outcome = "STOP_FIRST" if not target_hit else "DUAL_HIT_STOP_FIRST_CONSERVATIVE"
            exit_price = stop_price
        elif target_hit:
            outcome = "TARGET_FIRST"
            exit_price = target_price
        else:
            continue
        event_date = str(row["date"])
        sessions_to_event = index
        break
    gross = _pct(exit_price, entry_open)
    net = gross - cost_pct
    mfe = max(_pct(float(row["high"]), entry_open) for row in path_rows)
    mae = min(_pct(float(row["low"]), entry_open) for row in path_rows)
    return {
        "entry_market_date": str(path_rows[0]["date"]),
        "entry_adjusted_open": float(entry_open),
        "exit_market_date": event_date,
        "exit_adjusted_price": float(exit_price),
        "gross_return_pct": gross,
        "net_return_pct": net,
        "target_first_label": int(outcome == "TARGET_FIRST"),
        "path_outcome": outcome,
        "sessions_to_exit": sessions_to_event,
        "maximum_favorable_excursion_pct": mfe,
        "maximum_adverse_excursion_pct": mae,
    }


def fit_isotonic(raw: np.ndarray, labels: np.ndarray) -> dict[str, Any]:
    order = np.argsort(raw, kind="mergesort")
    values = raw[order]
    outcomes = labels[order]
    blocks: list[dict[str, float]] = []
    for value in np.unique(values):
        selected = outcomes[values == value]
        blocks.append({"upper": float(value), "count": float(len(selected)), "successes": float(selected.sum())})
        while len(blocks) >= 2:
            left, right = blocks[-2], blocks[-1]
            if left["successes"] / left["count"] <= right["successes"] / right["count"] + 1e-15:
                break
            blocks[-2:] = [{
                "upper": right["upper"],
                "count": left["count"] + right["count"],
                "successes": left["successes"] + right["successes"],
            }]
    return {
        "method": "isotonic_pava",
        "blocks": [
            {
                "upper_raw_score": block["upper"],
                "count": int(block["count"]),
                "successes": int(block["successes"]),
                "probability": block["successes"] / block["count"],
            }
            for block in blocks
        ],
    }


def apply_isotonic(raw: np.ndarray, calibrator: Mapping[str, Any]) -> np.ndarray:
    blocks = calibrator["blocks"]
    upper = np.asarray([block["upper_raw_score"] for block in blocks], dtype=float)
    index = np.clip(np.searchsorted(upper, raw, side="left"), 0, len(blocks) - 1)
    return np.asarray([blocks[item]["probability"] for item in index], dtype=float)


def probability_metrics(labels: np.ndarray, probabilities: np.ndarray, baseline_rate: float) -> dict[str, float]:
    brier = float(np.mean(np.square(probabilities - labels)))
    baseline = float(np.mean(np.square(baseline_rate - labels)))
    ece = 0.0
    for index in range(10):
        low, high = index / 10.0, (index + 1) / 10.0
        selected = (probabilities >= low) & ((probabilities < high) if index < 9 else (probabilities <= high))
        if np.any(selected):
            ece += float(np.mean(selected)) * abs(float(np.mean(probabilities[selected])) - float(np.mean(labels[selected])))
    return {
        "brier": brier,
        "brier_skill_pct": 0.0 if baseline <= 0 else (baseline - brier) / baseline * 100.0,
        "ece_10bin": ece,
    }


def trade_metrics(rows: Sequence[Mapping[str, Any]], all_rows: Sequence[Mapping[str, Any]], *, account: float, notional: float) -> dict[str, Any]:
    returns = [float(row["net_return_pct"]) for row in rows]
    positive = [value for value in returns if value > 0]
    nonpositive = [value for value in returns if value <= 0]
    gross_profit = sum(positive)
    gross_loss = -sum(nonpositive)
    realized: dict[str, float] = {}
    for row in rows:
        realized[str(row["exit_market_date"])] = realized.get(str(row["exit_market_date"]), 0.0) + notional * float(row["net_return_pct"]) / 100.0
    capital = peak = account
    drawdown = 0.0
    for exit_date in sorted(realized):
        capital += realized[exit_date]
        peak = max(peak, capital)
        drawdown = min(drawdown, (capital / peak - 1.0) * 100.0)
    standard = float(np.std(returns, ddof=1)) if len(returns) >= 2 else 0.0
    downside = float(np.std([min(value, 0.0) for value in returns], ddof=1)) if len(returns) >= 2 else 0.0
    observed_months = len({str(row["market_date"])[:7] for row in all_rows})
    return {
        "candidates": len(rows),
        "candidate_dates": len({str(row["market_date"]) for row in rows}),
        "observed_months": observed_months,
        "trades_per_observed_month": len(rows) / observed_months if observed_months else 0.0,
        "mean_net_return_pct": mean(returns) if returns else None,
        "median_net_return_pct": median(returns) if returns else None,
        "target_first_rate_pct": mean(int(row["target_first_label"]) for row in rows) * 100.0 if rows else None,
        "average_winner_pct": mean(positive) if positive else None,
        "average_loser_pct": mean(nonpositive) if nonpositive else None,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0),
        "sharpe_per_trade": mean(returns) / standard if returns and standard > 0 else 0.0,
        "sortino_per_trade": mean(returns) / downside if returns and downside > 0 else 0.0,
        "maximum_drawdown_pct": drawdown,
        "ending_research_capital": capital,
    }
