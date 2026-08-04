import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from refresh_sp500_daily_incremental import (
    append_only,
    fetch_recent,
    stored_candle_date_for_session,
    symbols_before_date,
)


class IncrementalDailyRefreshTests(unittest.TestCase):
    @patch("refresh_sp500_daily_incremental.time.time", return_value=1_785_799_729.0)
    @patch("refresh_sp500_daily_incremental.schwab_get_json")
    def test_fetch_recent_anchors_history_to_current_time(self, get_json, _time):
        get_json.return_value = {
            "candles": [{"datetime": 1_785_729_600_000, "close": 251.34}]
        }

        variant, candles = fetch_recent("ADBE")

        self.assertEqual("ADBE", variant)
        self.assertEqual(1, len(candles))
        params = get_json.call_args.args[1]
        self.assertEqual(1_785_799_729_000, params["endDate"])
        self.assertEqual("true", params["needPreviousClose"])

    def test_appends_only_dates_after_existing_latest(self):
        existing = [{"date": "2026-07-21", "close": "100"}]
        recent = [{"date": "2026-07-21", "close": "999"}, {"date": "2026-07-22", "close": "101"}]
        merged = append_only(existing, recent)
        self.assertEqual(["2026-07-21", "2026-07-22"], [row["date"] for row in merged])
        self.assertEqual("100", merged[0]["close"])

    def test_does_not_append_stale_data(self):
        self.assertEqual([{"date": "2026-07-22"}], append_only([{"date": "2026-07-22"}], [{"date": "2026-07-21"}]))

    def test_max_candle_date_excludes_in_progress_day(self):
        existing = [{"date": "2026-07-27"}]
        recent = [{"date": "2026-07-28"}, {"date": "2026-07-29"}, {"date": "2026-07-30"}]
        self.assertEqual(
            [{"date": "2026-07-27"}, {"date": "2026-07-28"}, {"date": "2026-07-29"}],
            append_only(existing, recent, max_candle_date="2026-07-29"),
        )

    def test_session_date_translates_to_prior_pacific_storage_key(self):
        self.assertEqual(
            "2026-08-03", stored_candle_date_for_session("2026-08-04")
        )

    def test_selects_only_existing_stale_histories(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A_schwab_1d_max.csv").write_text("date\n2026-07-21\n", encoding="utf-8")
            (root / "B_schwab_1d_max.csv").write_text("date\n2026-07-22\n", encoding="utf-8")
            self.assertEqual(["A"], symbols_before_date(["A", "B", "C"], root, "2026-07-22"))


if __name__ == "__main__":
    unittest.main()
