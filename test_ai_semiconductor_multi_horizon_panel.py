import unittest

from build_ai_semiconductor_multi_horizon_panel import build_panel, horizon_labels


class MultiHorizonPanelTests(unittest.TestCase):
    def setUp(self):
        self.daily = [
            ("2026-01-02", 100.0, 100.0),
            ("2026-01-05", 101.0, 102.0),
            ("2026-01-06", 103.0, 104.0),
            ("2026-01-07", 105.0, 106.0),
            ("2026-01-08", 107.0, 108.0),
            ("2026-01-09", 109.0, 110.0),
        ]

    def test_labels_use_next_open_and_fixed_session_closes(self):
        labels = horizon_labels(self.daily, "2026-01-02", horizons=(1, 5))
        self.assertEqual(labels["label_entry_market_date"], "2026-01-05")
        self.assertEqual(labels["label_entry_next_open"], 101.0)
        self.assertEqual(labels["label_1d_exit_market_date"], "2026-01-05")
        self.assertEqual(labels["label_5d_exit_market_date"], "2026-01-09")
        self.assertAlmostEqual(labels["label_1d_net_return_pct"], (102 / 101 - 1) * 100 - 0.25)
        self.assertAlmostEqual(labels["label_5d_net_return_pct"], (110 / 101 - 1) * 100 - 0.25)

    def test_unavailable_long_horizon_is_explicit(self):
        labels = horizon_labels(self.daily, "2026-01-02", horizons=(20,))
        self.assertFalse(labels["label_20d_available"])
        self.assertIsNone(labels["label_20d_net_return_pct"])

    def test_duplicate_keys_fail_closed(self):
        rows = [{"symbol": "AMD", "market_date": "2026-01-02"}] * 2
        with self.assertRaises(ValueError):
            build_panel(rows, {"AMD": self.daily})


if __name__ == "__main__":
    unittest.main()
