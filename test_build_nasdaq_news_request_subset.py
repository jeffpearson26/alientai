from __future__ import annotations

import unittest

from build_nasdaq_news_request_subset import select_requests


class NasdaqNewsRequestSubsetTests(unittest.TestCase):
    def test_selects_and_sorts_only_requested_symbols(self) -> None:
        rows = [
            {"symbol": "ZZZ", "as_of_utc": "2026-01-03T21:00:00+00:00"},
            {"symbol": "aaa", "as_of_utc": "2026-01-04T21:00:00+00:00"},
            {"symbol": "AAA", "as_of_utc": "2026-01-03T21:00:00+00:00"},
        ]
        result = select_requests(rows, {"AAA"})
        self.assertEqual([row["as_of_utc"][:10] for row in result], ["2026-01-03", "2026-01-04"])

    def test_rejects_empty_subset(self) -> None:
        with self.assertRaisesRegex(ValueError, "no Nasdaq"):
            select_requests([{"symbol": "ZZZ", "as_of_utc": "2026-01-03T21:00:00+00:00"}], {"AAA"})

    def test_rejects_conflicting_duplicate(self) -> None:
        rows = [
            {"symbol": "AAA", "as_of_utc": "2026-01-03T21:00:00+00:00", "x": 1},
            {"symbol": "AAA", "as_of_utc": "2026-01-03T21:00:00+00:00", "x": 2},
        ]
        with self.assertRaisesRegex(ValueError, "conflicting"):
            select_requests(rows, {"AAA"})


if __name__ == "__main__":
    unittest.main()
