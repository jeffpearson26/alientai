from __future__ import annotations

import unittest

from compile_historical_option_features import unique_event_closes


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


if __name__ == "__main__":
    unittest.main()
