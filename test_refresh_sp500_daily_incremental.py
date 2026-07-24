import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from refresh_sp500_daily_incremental import append_only, symbols_before_date


class IncrementalDailyRefreshTests(unittest.TestCase):
    def test_appends_only_dates_after_existing_latest(self):
        existing = [{"date": "2026-07-21", "close": "100"}]
        recent = [{"date": "2026-07-21", "close": "999"}, {"date": "2026-07-22", "close": "101"}]
        merged = append_only(existing, recent)
        self.assertEqual(["2026-07-21", "2026-07-22"], [row["date"] for row in merged])
        self.assertEqual("100", merged[0]["close"])

    def test_does_not_append_stale_data(self):
        self.assertEqual([{"date": "2026-07-22"}], append_only([{"date": "2026-07-22"}], [{"date": "2026-07-21"}]))

    def test_selects_only_existing_stale_histories(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A_schwab_1d_max.csv").write_text("date\n2026-07-21\n", encoding="utf-8")
            (root / "B_schwab_1d_max.csv").write_text("date\n2026-07-22\n", encoding="utf-8")
            self.assertEqual(["A"], symbols_before_date(["A", "B", "C"], root, "2026-07-22"))


if __name__ == "__main__":
    unittest.main()
