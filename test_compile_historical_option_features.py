from __future__ import annotations

import unittest

from compile_historical_option_features import unique_event_closes
from download_alpha_vantage_historical_options import event_requests, is_transient_error


class HistoricalOptionCompilerTests(unittest.TestCase):
    def test_duplicate_study_rows_produce_one_key(self):
        rows = [
            {"symbol": "AAA", "market_date": "2024-01-02", "close": 10.0},
            {"symbol": "AAA", "market_date": "2024-01-02", "close": 10.0},
        ]
        self.assertEqual({("AAA", "2024-01-02"): 10.0}, unique_event_closes(rows))

    def test_inconsistent_duplicate_close_fails_closed(self):
        rows = [
            {"symbol": "AAA", "market_date": "2024-01-02", "close": 10.0},
            {"symbol": "AAA", "market_date": "2024-01-02", "close": 11.0},
        ]
        with self.assertRaises(ValueError):
            unique_event_closes(rows)

    def test_market_date_only_excludes_future_snapshot(self):
        rows = [{"symbol": "AAA", "market_date": "2026-01-02", "future_market_date": "2026-01-09"}]
        self.assertEqual([("AAA", "2026-01-02")], event_requests(rows, role="all", include_future_date=False))

    def test_temporary_server_errors_are_retryable(self):
        self.assertTrue(is_transient_error(RuntimeError("HTTP 503 service unavailable")))
        self.assertFalse(is_transient_error(RuntimeError("Invalid ticker format")))


if __name__ == "__main__":
    unittest.main()
