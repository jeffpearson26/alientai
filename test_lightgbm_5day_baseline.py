import unittest
from unittest.mock import patch

import numpy as np

from train_v2_lightgbm_5day_sp500_from_supabase import (
    feature_names,
    fetch_symbol_candles,
    make_symbol_examples,
    non_overlapping_indices,
    summarize_sequence,
    threshold_metrics,
)


class LightGBMFiveDayBaselineTests(unittest.TestCase):
    @patch("train_v2_lightgbm_5day_sp500_from_supabase.fetch_daily_candles")
    def test_supabase_helper_receives_current_keyword_interface(self, mocked_fetch):
        mocked_fetch.return_value = [{"close": 1.0}]
        result = fetch_symbol_candles(
            supabase_url="https://example.supabase.co",
            supabase_key="secret",
            table="v2_daily_candles",
            symbol="AAPL",
            limit=10000,
        )
        self.assertEqual(result, [{"close": 1.0}])
        mocked_fetch.assert_called_once_with(
            supabase_url="https://example.supabase.co",
            supabase_key="secret",
            table="v2_daily_candles",
            symbol="AAPL",
            limit=10000,
        )

    def test_summary_shape_matches_names(self):
        sequence = np.arange(60 * 16, dtype=np.float32).reshape(60, 16)
        result = summarize_sequence(sequence)
        self.assertEqual(result.shape, (len(feature_names()),))
        self.assertEqual(len(feature_names()), 272)

    def test_summary_rejects_short_sequence(self):
        with self.assertRaises(ValueError):
            summarize_sequence(np.zeros((59, 16), dtype=np.float32))

    def test_five_day_label_uses_future_close_only(self):
        candles = []
        for i in range(280):
            close = 100.0 + i
            candles.append({
                "date": f"d{i}", "datetime_ms": (i + 1) * 86_400_000,
                "open": close - 0.5, "high": close + 1, "low": close - 1,
                "close": close, "volume": 1_000 + i,
            })
        x, labels, returns, meta = make_symbol_examples(
            symbol="TEST", candles=candles, sequence_length=60, horizon_days=5,
            min_history_days=260, step_days=1, target_return_pct=0.0,
        )
        self.assertTrue(x)
        self.assertTrue(all(label == 1 for label in labels))
        self.assertEqual(meta[0]["datetime_ms"], candles[260]["datetime_ms"])
        self.assertAlmostEqual(returns[0], ((candles[265]["close"] / candles[260]["close"]) - 1) * 100)

    def test_non_overlapping_is_per_symbol(self):
        metadata = [
            {"symbol": "A", "datetime_ms": 1 * 86_400_000},
            {"symbol": "B", "datetime_ms": 2 * 86_400_000},
            {"symbol": "A", "datetime_ms": 3 * 86_400_000},
            {"symbol": "A", "datetime_ms": 12 * 86_400_000},
        ]
        kept = non_overlapping_indices(metadata, np.ones(4, dtype=bool), 9)
        self.assertEqual(kept.tolist(), [0, 1, 3])

    def test_metrics_subtract_round_trip_cost(self):
        labels = np.array([1, 0, 1])
        probabilities = np.array([0.8, 0.7, 0.2])
        returns = np.array([1.0, -0.5, 2.0])
        metadata = [
            {"symbol": "A", "datetime_ms": 1 * 86_400_000},
            {"symbol": "B", "datetime_ms": 1 * 86_400_000},
            {"symbol": "C", "datetime_ms": 1 * 86_400_000},
        ]
        result = threshold_metrics(labels, probabilities, returns, metadata, 0.6, 0.25, 9)
        self.assertEqual(result["signal_count"], 2)
        self.assertAlmostEqual(result["avg_net_return_pct"], 0.0)
        self.assertAlmostEqual(result["cost_adjusted_win_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
