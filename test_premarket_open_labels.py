from __future__ import annotations

import unittest

from alientai_v2.research.premarket_open_labels import build_open_entry_label


def candle(stamp, close):
    return {"timestamp": stamp, "close": close}


class PremarketOpenLabelTests(unittest.TestCase):
    def test_entry_uses_first_regular_bar_close_not_premarket_or_daily_close(self):
        entry = [
            candle("2024-01-02 09:25:00", 90),
            candle("2024-01-02 09:30:00", 100),
            candle("2024-01-02 09:35:00", 110),
            candle("2024-01-02 16:00:00", 120),
        ]
        exit_ = [candle("2024-01-09 09:30:00", 125), candle("2024-01-09 16:00:00", 130)]
        result = build_open_entry_label(entry, exit_, "2024-01-02", "2024-01-09")
        self.assertEqual(result["premarket_entry_price"], 100)
        self.assertEqual(result["premarket_exit_price"], 130)
        self.assertAlmostEqual(result["premarket_forward_return_5d_pct"], 30.0)
        self.assertTrue(result["premarket_label_exceptional_winner"])

    def test_missing_entry_or_exit_fails_closed(self):
        result = build_open_entry_label([], [], "2024-01-02", "2024-01-09")
        self.assertFalse(result["premarket_label_available"])
        self.assertIsNone(result["premarket_label_exceptional_winner"])


if __name__ == "__main__":
    unittest.main()
