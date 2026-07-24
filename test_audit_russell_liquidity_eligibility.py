import unittest

from audit_russell_liquidity_eligibility import eligibility_counts


class RussellLiquidityEligibilityTests(unittest.TestCase):
    def test_uses_only_trailing_dollar_volume_at_each_row(self):
        candles = [
            {"date": "2026-01-01", "close": "4", "volume": "2000000"},
            {"date": "2026-01-02", "close": "6", "volume": "1000000"},
            {"date": "2026-01-05", "close": "6", "volume": "1000000"},
            {"date": "2026-01-06", "close": "6", "volume": "1000000"},
        ]
        result = eligibility_counts(candles, min_price=5.0, min_avg_dollar_volume=5_000_000.0, lookback_days=2)
        self.assertEqual(result["checked_rows"], 3)
        self.assertEqual(result["eligible_rows"], 3)

    def test_counts_extreme_forward_moves_without_using_them_for_eligibility(self):
        candles = [{"date": f"2026-01-{day:02d}", "close": "10", "volume": "1000000"} for day in range(1, 8)]
        candles[6]["close"] = "21"
        result = eligibility_counts(candles, min_price=5.0, min_avg_dollar_volume=1_000_000.0, lookback_days=2)
        self.assertEqual(result["eligible_rows"], 6)
        self.assertEqual(result["five_day_returns_over_100pct"], 1)

    def test_rejects_liquidity_window_with_long_date_gap(self):
        candles = [
            {"date": "2026-01-02", "close": "10", "volume": "100000"},
            {"date": "2026-06-02", "close": "10", "volume": "100000"},
            {"date": "2026-06-03", "close": "10", "volume": "100000"},
        ]
        result = eligibility_counts(candles, min_price=5.0, min_avg_dollar_volume=1_000_000.0, lookback_days=2)
        self.assertEqual(result["checked_rows"], 2)
        self.assertEqual(result["continuous_checked_rows"], 1)
        self.assertEqual(result["eligible_rows"], 1)


if __name__ == "__main__":
    unittest.main()
