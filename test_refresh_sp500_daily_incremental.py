import unittest

from refresh_sp500_daily_incremental import append_only


class IncrementalDailyRefreshTests(unittest.TestCase):
    def test_appends_only_dates_after_existing_latest(self):
        existing = [{"date": "2026-07-21", "close": "100"}]
        recent = [{"date": "2026-07-21", "close": "999"}, {"date": "2026-07-22", "close": "101"}]
        merged = append_only(existing, recent)
        self.assertEqual(["2026-07-21", "2026-07-22"], [row["date"] for row in merged])
        self.assertEqual("100", merged[0]["close"])

    def test_does_not_append_stale_data(self):
        self.assertEqual([{"date": "2026-07-22"}], append_only([{"date": "2026-07-22"}], [{"date": "2026-07-21"}]))


if __name__ == "__main__":
    unittest.main()
