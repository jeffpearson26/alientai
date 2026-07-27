from __future__ import annotations

import unittest

from alientai_v2.features.premarket_features import build_premarket_features
from build_matched_premarket_features import build_rows


def candle(stamp, close, volume=100, high=None, low=None):
    return {
        "timestamp": stamp, "open": close, "high": high if high is not None else close,
        "low": low if low is not None else close, "close": close, "volume": volume,
    }


class PremarketFeatureTests(unittest.TestCase):
    def test_natural_rows_do_not_acquire_study_metadata(self):
        rows = build_rows(
            [{"symbol": "", "market_date": "2026-01-02"}],
            archive=__import__("pathlib").Path("unused"),
        )
        self.assertEqual(rows[0]["premarket_available"], False)
        self.assertFalse(any(key.startswith("study_") for key in rows[0]))

    def test_uses_only_bars_through_0925(self):
        rows = [
            candle("2024-01-02 16:00:00", 100),
            candle("2024-01-03 04:00:00", 101),
            candle("2024-01-03 08:25:00", 102),
            candle("2024-01-03 08:55:00", 103),
            candle("2024-01-03 09:25:00", 104, high=105, low=103),
            candle("2024-01-03 09:30:00", 999, volume=999999),
        ]
        result = build_premarket_features(rows, "2024-01-03")
        self.assertEqual(result["premarket_last_close"], 104)
        self.assertAlmostEqual(result["premarket_gap_pct"], 4.0)
        self.assertEqual(result["premarket_bar_count"], 4)
        self.assertEqual(result["premarket_volume"], 400)
        self.assertAlmostEqual(result["premarket_return_30m_pct"], (104 / 103 - 1) * 100)
        self.assertAlmostEqual(result["premarket_return_60m_pct"], (104 / 102 - 1) * 100)

    def test_relative_volume_uses_prior_premarket_sessions(self):
        rows = [
            candle("2024-01-01 08:00:00", 10, 100),
            candle("2024-01-02 08:00:00", 10, 300),
            candle("2024-01-03 08:00:00", 10, 400),
        ]
        result = build_premarket_features(rows, "2024-01-03")
        self.assertEqual(result["premarket_typical_prior_volume"], 200)
        self.assertEqual(result["premarket_relative_volume"], 2.0)

    def test_missing_premarket_fails_closed(self):
        result = build_premarket_features([], "2024-01-03")
        self.assertFalse(result["premarket_available"])
        self.assertEqual(result["premarket_bar_count"], 0)


if __name__ == "__main__":
    unittest.main()
