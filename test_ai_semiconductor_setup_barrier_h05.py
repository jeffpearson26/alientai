from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from alientai_v2.research.ai_semiconductor_setup_barrier_h05 import (
    ENGINE_NAMES,
    FEATURE_NAMES,
    apply_isotonic,
    build_feature_values,
    detect_setups,
    fit_isotonic,
    resolve_path_label,
)


def candles(count: int = 70, *, daily_gain: float = 0.002, volume: float = 1_000_000.0):
    rows = []
    current = date(2024, 1, 2)
    close = 100.0
    for index in range(count):
        while current.weekday() >= 5:
            current += timedelta(days=1)
        prior = close
        close *= 1.0 + daily_gain
        rows.append({
            "date": current.isoformat(),
            "open": prior * 1.0005,
            "high": close * 1.006,
            "low": prior * 0.996,
            "close": close,
            "volume": volume * (1.0 + (index % 5) * 0.01),
        })
        current += timedelta(days=1)
    return rows


def test_feature_contract_is_finite_and_exact() -> None:
    stock = candles(daily_gain=0.003)
    contexts = {
        "QQQ": candles(daily_gain=0.0015),
        "SOXX": candles(daily_gain=0.0018),
        "SPY": candles(daily_gain=0.0010),
        "VIXY": candles(daily_gain=-0.0010),
    }
    features = build_feature_values(
        stock,
        contexts,
        {"above_20dma_fraction": 0.8, "green_fraction": 0.7, "median_return_1d_pct": 0.2},
    )
    assert list(features) == FEATURE_NAMES
    assert len(features) == 49
    assert all(np.isfinite(value) for value in features.values())
    assert features["relative_strength_acceleration_soxx"] == (
        features["stock_minus_soxx_5d_pct"] - features["stock_minus_soxx_20d_pct"] / 4.0
    )


def test_setup_detector_can_abstain_and_identify_each_engine() -> None:
    base = {name: 0.0 for name in FEATURE_NAMES}
    assert detect_setups(base) == {name: False for name in ENGINE_NAMES}
    pullback = dict(base)
    pullback.update({
        "ema20_distance_pct": 2.0,
        "ema50_distance_pct": 4.0,
        "ema20_minus_ema50_pct": 2.0,
        "ema20_slope_5d_pct": 0.5,
        "stock_minus_soxx_20d_pct": 1.0,
        "return_3d_pct": -2.0,
        "pullback_volume_ratio_3_vs_prior10": 0.8,
        "distance_from_20d_high_pct": -5.0,
    })
    assert detect_setups(pullback)["PULLBACK_CONTINUATION_V1"]
    breakout = dict(base)
    breakout.update({
        "ema20_distance_pct": 1.0,
        "range_position_20": 0.85,
        "distance_from_20d_high_pct": -2.0,
        "range_compression_5_vs20": 0.7,
        "atr_contraction_5_vs20": 0.8,
        "relative_strength_acceleration_soxx": 0.5,
    })
    assert detect_setups(breakout)["BREAKOUT_ANTICIPATION_V1"]
    sector = dict(base)
    sector.update({
        "soxx_return_1d_pct": 1.0,
        "qqq_return_1d_pct": 0.3,
        "universe_green_fraction": 0.8,
        "universe_above_20dma_fraction": 0.7,
        "vixy_proxy_return_1d_pct": -2.0,
        "return_1d_pct": 1.2,
        "stock_minus_soxx_5d_pct": -1.0,
    })
    assert detect_setups(sector)["SECTOR_RIP_MOMENTUM_V1"]


def test_path_label_target_stop_dual_and_timeout() -> None:
    def path(first_high: float, first_low: float, final_close: float = 101.0):
        return [
            {"date": f"2025-01-{index + 2:02d}", "open": 100.0, "high": first_high if index == 0 else 102.0, "low": first_low if index == 0 else 99.0, "close": final_close if index == 4 else 100.0}
            for index in range(5)
        ]
    target = resolve_path_label(path(103.1, 99.0), entry_open=100.0, target_pct=3.0, stop_pct=1.5, cost_pct=0.25)
    assert target["path_outcome"] == "TARGET_FIRST"
    assert target["target_first_label"] == 1
    assert abs(target["net_return_pct"] - 2.75) < 1e-12
    stop = resolve_path_label(path(102.0, 98.4), entry_open=100.0, target_pct=3.0, stop_pct=1.5, cost_pct=0.25)
    assert stop["path_outcome"] == "STOP_FIRST"
    assert abs(stop["net_return_pct"] + 1.75) < 1e-12
    dual = resolve_path_label(path(103.1, 98.4), entry_open=100.0, target_pct=3.0, stop_pct=1.5, cost_pct=0.25)
    assert dual["path_outcome"] == "DUAL_HIT_STOP_FIRST_CONSERVATIVE"
    assert dual["target_first_label"] == 0
    timeout = resolve_path_label(path(102.0, 99.0, 101.0), entry_open=100.0, target_pct=3.0, stop_pct=1.5, cost_pct=0.25)
    assert timeout["path_outcome"] == "TIMEOUT"
    assert abs(timeout["net_return_pct"] - 0.75) < 1e-12


def test_isotonic_calibrator_is_monotone() -> None:
    raw = np.asarray([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    labels = np.asarray([0, 1, 0, 1, 1, 1])
    calibrator = fit_isotonic(raw, labels)
    probabilities = apply_isotonic(np.linspace(0.1, 0.6, 30), calibrator)
    assert np.all(np.diff(probabilities) >= -1e-15)
    assert np.all((probabilities >= 0.0) & (probabilities <= 1.0))
