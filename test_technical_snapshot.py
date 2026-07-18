from __future__ import annotations

import unittest

from alientai_v2.features.technical_snapshot import build_technical_snapshot


def candles(count=60, future_jump=0.0):
    rows = []
    for index in range(count):
        close = 100.0 + index * 0.5
        if index == count - 1:
            close += future_jump
        rows.append({
            "close": close, "high": close + 1.0, "low": close - 1.0,
            "volume": 1000 + index * 10,
        })
    return rows


class TechnicalSnapshotTests(unittest.TestCase):
    def test_requires_sixty_prior_and_current_candles(self):
        with self.assertRaises(ValueError):
            build_technical_snapshot(candles(59))

    def test_expected_feature_families_exist(self):
        result = build_technical_snapshot(candles())
        for key in (
            "technical_rsi_14", "technical_macd_histogram_pct", "technical_atr14_pct",
            "technical_adx14", "technical_bollinger_width_pct",
            "technical_relative_volume_10_vs_20", "technical_obv_change_10d_normalized",
        ):
            self.assertIn(key, result)
        self.assertTrue(result["technical_ema_bullish_alignment"])

    def test_current_candle_changes_snapshot(self):
        normal = build_technical_snapshot(candles())
        jumped = build_technical_snapshot(candles(future_jump=20.0))
        self.assertNotEqual(normal["technical_macd_histogram_pct"], jumped["technical_macd_histogram_pct"])
        self.assertNotEqual(normal["technical_latest_relative_volume_20"], 0.0)

    def test_missing_high_low_and_volume_remains_safe(self):
        result = build_technical_snapshot([{"close": 100 + index} for index in range(60)])
        self.assertGreaterEqual(result["technical_atr14_pct"], 0.0)
        self.assertEqual(result["technical_relative_volume_10_vs_20"], 0.0)


if __name__ == "__main__":
    unittest.main()
