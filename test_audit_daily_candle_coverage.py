import unittest

from audit_daily_candle_coverage import latest_day, summarize_latest_days


class DailyCandleCoverageTests(unittest.TestCase):
    def test_latest_day_uses_latest_valid_utc_date(self):
        rows = [
            {"datetime_utc": "2026-07-01T22:00:00+00:00"},
            {"datetime_utc": "2026-07-09T22:00:00+00:00"},
            {"datetime_utc": "not-a-date"},
        ]
        self.assertEqual(latest_day(rows), "2026-07-09")

    def test_summary_keeps_missing_symbols_and_distribution(self):
        report = summarize_latest_days({"A": "2026-07-09", "B": "2026-07-09", "C": "2026-07-08", "D": None})
        self.assertEqual(report["symbols_requested"], 4)
        self.assertEqual(report["symbols_with_daily_history"], 3)
        self.assertEqual(report["symbols_without_daily_history"], ["D"])
        self.assertEqual(report["newest_available_market_date"], "2026-07-09")
        self.assertEqual(report["symbols_at_newest_date"], 2)


if __name__ == "__main__":
    unittest.main()
