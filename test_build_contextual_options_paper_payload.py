import unittest

from build_contextual_options_paper_payload import matched_rows


class ContextualOptionsPaperPayloadTests(unittest.TestCase):
    def test_uses_only_exact_common_keys(self):
        technical = [
            {"symbol": "AAA", "market_date": "2026-07-27", "a": 1},
            {"symbol": "BBB", "market_date": "2026-07-27", "a": 2},
        ]
        options = [
            {"symbol": "AAA", "market_date": "2026-07-27", "b": 3},
            {"symbol": "CCC", "market_date": "2026-07-27", "b": 4},
        ]
        rows = matched_rows(technical, options, minimum_rows=1)
        self.assertEqual([{"symbol": "AAA", "market_date": "2026-07-27", "a": 1, "b": 3}], rows)

    def test_fails_closed_below_minimum(self):
        with self.assertRaises(ValueError):
            matched_rows(
                [{"symbol": "AAA", "market_date": "2026-07-27"}],
                [{"symbol": "AAA", "market_date": "2026-07-27"}],
                minimum_rows=2,
            )


if __name__ == "__main__":
    unittest.main()
