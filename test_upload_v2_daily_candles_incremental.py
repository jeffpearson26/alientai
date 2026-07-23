import unittest

from upload_v2_daily_candles_incremental import rows_newer_than


class IncrementalDailyUploaderTests(unittest.TestCase):
    def test_keeps_only_strictly_newer_rows(self):
        rows = [{"datetime_ms": 10}, {"datetime_ms": 20}, {"datetime_ms": 30}]
        self.assertEqual(rows_newer_than(rows, 20), [{"datetime_ms": 30}])

    def test_missing_remote_history_keeps_all_valid_rows(self):
        rows = [{"datetime_ms": 10}, {"datetime_ms": 20}]
        self.assertEqual(rows_newer_than(rows, None), rows)


if __name__ == "__main__":
    unittest.main()
