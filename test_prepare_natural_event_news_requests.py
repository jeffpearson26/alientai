import tempfile
import unittest
from pathlib import Path

from prepare_natural_event_news_requests import prepare_requests, read_jsonl, write_jsonl


class NaturalEventNewsRequestTests(unittest.TestCase):
    def test_prepares_sorted_natural_requests(self):
        rows = [
            {"symbol": "msft", "market_date": "2026-01-03", "as_of_utc": "2026-01-03T21:00:00+00:00"},
            {"symbol": "aapl", "market_date": "2026-01-02", "as_of_utc": "2026-01-02T21:00:00+00:00"},
        ]
        self.assertEqual(
            prepare_requests(rows),
            [
                {"symbol": "AAPL", "market_date": "2026-01-02", "as_of_utc": "2026-01-02T21:00:00+00:00", "study_role": "natural"},
                {"symbol": "MSFT", "market_date": "2026-01-03", "as_of_utc": "2026-01-03T21:00:00+00:00", "study_role": "natural"},
            ],
        )

    def test_duplicate_point_in_time_request_fails_closed(self):
        rows = [
            {"symbol": "AAPL", "market_date": "2026-01-02", "as_of_utc": "2026-01-02T21:00:00+00:00"},
            {"symbol": "AAPL", "market_date": "2026-01-02", "as_of_utc": "2026-01-02T21:00:00+00:00"},
        ]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            prepare_requests(rows)

    def test_round_trips_jsonl(self):
        rows = prepare_requests([
            {"symbol": "AAPL", "market_date": "2026-01-02", "as_of_utc": "2026-01-02T21:00:00+00:00"},
        ])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "requests.jsonl"
            write_jsonl(path, rows)
            self.assertEqual(list(read_jsonl(path)), rows)


if __name__ == "__main__":
    unittest.main()
