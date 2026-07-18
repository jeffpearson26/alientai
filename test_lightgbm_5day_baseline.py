import unittest
from unittest.mock import patch

import numpy as np

from train_v2_lightgbm_5day_sp500_from_supabase import (
    feature_names,
    fetch_symbol_candles,
    fetch_symbol_candles_with_retry,
    make_symbol_examples,
    non_overlapping_indices,
    summarize_sequence,
    threshold_metrics,
    train_native_models,
)


class LightGBMFiveDayBaselineTests(unittest.TestCase):
    @patch("train_v2_lightgbm_5day_sp500_from_supabase.time.sleep")
    @patch("train_v2_lightgbm_5day_sp500_from_supabase.fetch_symbol_candles")
    def test_transient_fetch_failure_retries_complete_symbol(self, mocked_fetch, mocked_sleep):
        mocked_fetch.side_effect = [RuntimeError("temporary"), [{"close": 2.0}]]
        result = fetch_symbol_candles_with_retry(
            supabase_url="https://example.supabase.co", supabase_key="secret",
            table="v2_daily_candles", symbol="AAPL", limit=10000,
            attempts=3, base_delay_seconds=0.01,
        )
        self.assertEqual(result, [{"close": 2.0}])
        self.assertEqual(mocked_fetch.call_count, 2)
        mocked_sleep.assert_called_once_with(0.01)

    @patch("train_v2_lightgbm_5day_sp500_from_supabase.time.sleep")
    @patch("train_v2_lightgbm_5day_sp500_from_supabase.fetch_symbol_candles")
    def test_fetch_retry_fails_closed_after_limit(self, mocked_fetch, mocked_sleep):
        mocked_fetch.side_effect = RuntimeError("still unavailable")
        with self.assertRaisesRegex(RuntimeError, "MSFT after 2 attempts"):
            fetch_symbol_candles_with_retry(
                supabase_url="https://example.supabase.co", supabase_key="secret",
                table="v2_daily_candles", symbol="MSFT", limit=10000,
                attempts=2, base_delay_seconds=0.0,
            )

    def test_native_lightgbm_training_does_not_require_sklearn_wrapper(self):
        rng = np.random.default_rng(42)
        x = rng.normal(size=(240, 4)).astype(np.float32)
        y = (x[:, 0] + x[:, 1] > 0).astype(np.int32)
        returns = (x[:, 0] * 0.8 + x[:, 1] * 0.4).astype(np.float32)
        classifier, regressor = train_native_models(
            x_train=x[:180], y_train=y[:180], returns_train=returns[:180],
            x_validation=x[180:], y_validation=y[180:], returns_validation=returns[180:],
            names=["a", "b", "c", "d"], num_boost_round=15, early_stopping_rounds=5,
        )
        class_predictions = classifier.predict(x[180:])
        return_predictions = regressor.predict(x[180:])
        self.assertEqual(class_predictions.shape, (60,))
        self.assertEqual(return_predictions.shape, (60,))
        self.assertGreater(classifier.best_iteration, 0)
        self.assertGreater(regressor.best_iteration, 0)

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
