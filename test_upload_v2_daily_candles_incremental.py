import unittest

from upload_v2_daily_candles_incremental import DEFAULT_SP500_INPUT_DIR, remote_symbol, rows_newer_than


class IncrementalDailyUploaderTests(unittest.TestCase):
    def test_default_input_is_refreshed_sp500_archive(self):
        self.assertEqual(DEFAULT_SP500_INPUT_DIR.name, "sp500_daily_schwab_max_history")

    def test_keeps_only_strictly_newer_rows(self):
        rows = [{"datetime_ms": 10}, {"datetime_ms": 20}, {"datetime_ms": 30}]
        self.assertEqual(rows_newer_than(rows, 20), [{"datetime_ms": 30}])

    def test_missing_remote_history_keeps_all_valid_rows(self):
        rows = [{"datetime_ms": 10}, {"datetime_ms": 20}]
        self.assertEqual(rows_newer_than(rows, None), rows)

    def test_remote_symbol_preserves_dot_share_class(self):
        self.assertEqual(remote_symbol([{"symbol": "BRK.B"}], "BRK-B"), "BRK.B")


if __name__ == "__main__":
    unittest.main()
