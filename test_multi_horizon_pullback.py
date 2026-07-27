import unittest

from alientai_v2.research.multi_horizon_pullback import (
    build_pullback_features,
    log_slope_pct_per_day,
)


def candles(closes):
    return [{"close": value} for value in closes]


class MultiHorizonPullbackTests(unittest.TestCase):
    def test_positive_exponential_path_has_positive_slope(self):
        prices = [100.0 * (1.001 ** index) for index in range(126)]
        self.assertGreater(log_slope_pct_per_day(prices[-20:]), 0.0)
        result = build_pullback_features(candles(prices))
        self.assertTrue(result["pullback_all_trend_slopes_positive"])
        self.assertFalse(result["pullback_setup_eligible"])

    def test_orderly_uptrend_with_recent_dip_is_eligible(self):
        prices = [100.0 * (1.003 ** index) for index in range(126)]
        prices[-5:] = [
            prices[-6] * 0.998,
            prices[-6] * 0.994,
            prices[-6] * 0.990,
            prices[-6] * 0.987,
            prices[-6] * 0.984,
        ]
        result = build_pullback_features(candles(prices))
        self.assertTrue(result["pullback_all_trend_slopes_positive"])
        self.assertLess(result["pullback_return_5d_pct"], 0.0)
        self.assertTrue(result["pullback_setup_eligible"])

    def test_long_term_downtrend_is_rejected(self):
        prices = [200.0 * (0.998 ** index) for index in range(126)]
        result = build_pullback_features(candles(prices))
        self.assertFalse(result["pullback_all_trend_slopes_positive"])
        self.assertFalse(result["pullback_setup_eligible"])

    def test_insufficient_or_invalid_history_fails_closed(self):
        with self.assertRaises(ValueError):
            build_pullback_features(candles([100.0] * 125))
        with self.assertRaises(ValueError):
            build_pullback_features(candles([100.0] * 125 + [0.0]))


if __name__ == "__main__":
    unittest.main()
