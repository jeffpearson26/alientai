import unittest
from datetime import date, timedelta

from build_local_technical_training_rows import build_rows


class LocalTechnicalTrainingRowsTests(unittest.TestCase):
    @staticmethod
    def candles(multiplier=1.0):
        start = date(2025, 1, 1)
        return [{
            "date": (start + timedelta(days=index)).isoformat(),
            "open": (100 + index) * multiplier,
            "high": (101 + index) * multiplier,
            "low": (99 + index) * multiplier,
            "close": (100 + index) * multiplier,
            "volume": 1000 + index,
        } for index in range(70)]

    def test_features_are_point_in_time_and_label_uses_fifth_future_close(self):
        start = date(2025, 1, 1)
        candles = [{
            "date": (start + timedelta(days=index)).isoformat(),
            "open": 100 + index, "high": 101 + index, "low": 99 + index,
            "close": 100 + index, "volume": 1000 + index,
        } for index in range(70)]
        rows = build_rows(candles, "AAA", start, start + timedelta(days=100))
        first = rows[0]
        self.assertEqual(first["market_date"], candles[59]["date"])
        self.assertEqual(first["future_market_date"], candles[64]["date"])
        expected = (float(candles[64]["close"]) / float(candles[59]["close"]) - 1.0) * 100.0
        self.assertAlmostEqual(first["label_forward_return_5d_pct"], expected)
        self.assertIn("technical_rsi_14", first)

    def test_optional_benchmark_features_use_only_same_or_prior_dates(self):
        candles = self.candles(multiplier=2.0)
        benchmark = self.candles(multiplier=1.0)
        rows = build_rows(
            candles,
            "AAA",
            date(2025, 1, 1),
            date(2025, 12, 31),
            benchmark_candles=benchmark,
            benchmark_symbol="QQQ",
        )
        self.assertEqual(rows[0]["benchmark_symbol"], "QQQ")
        self.assertAlmostEqual(rows[0]["technical_relative_return_5d_pct"], 0.0)
        self.assertAlmostEqual(rows[0]["technical_relative_return_20d_pct"], 0.0)
        self.assertAlmostEqual(rows[0]["technical_relative_return_60d_pct"], 0.0)

    def test_executable_labels_enter_next_open_and_exit_fifth_close(self):
        rows = build_rows(
            self.candles(),
            "AAA",
            date(2025, 1, 1),
            date(2025, 12, 31),
            entry_assumption="next_regular_session_open",
        )
        first = rows[0]
        self.assertEqual(first["market_date"], self.candles()[59]["date"])
        self.assertEqual(first["entry_market_date"], self.candles()[60]["date"])
        self.assertEqual(first["future_market_date"], self.candles()[64]["date"])
        expected = (float(self.candles()[64]["close"]) / float(self.candles()[60]["open"]) - 1.0) * 100.0
        self.assertAlmostEqual(first["label_forward_return_5d_pct"], expected)
        self.assertEqual(first["holding_sessions"], 5)

    def test_executable_labels_support_requested_horizon(self):
        rows = build_rows(
            self.candles(),
            "AAA",
            date(2025, 1, 1),
            date(2025, 12, 31),
            horizon_sessions=2,
            entry_assumption="next_regular_session_open",
        )
        self.assertTrue(rows)
        self.assertEqual(rows[0]["holding_sessions"], 2)
        self.assertEqual(rows[0]["future_market_date"], self.candles()[61]["date"])

    def test_benchmark_mode_skips_dates_without_required_history(self):
        candles = self.candles()
        benchmark = self.candles()[10:]
        rows = build_rows(
            candles,
            "AAA",
            date(2025, 1, 1),
            date(2025, 12, 31),
            benchmark_candles=benchmark,
            benchmark_symbol="QQQ",
        )
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
