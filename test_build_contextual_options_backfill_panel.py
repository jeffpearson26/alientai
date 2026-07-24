import unittest

from build_contextual_options_backfill_panel import index_unique


class ContextualOptionsBackfillPanelTests(unittest.TestCase):
    def test_duplicate_or_missing_key_fails_closed(self):
        with self.assertRaises(ValueError):
            index_unique([{"symbol": "ABC", "market_date": "2026-07-22"}, {"symbol": "ABC", "market_date": "2026-07-22"}], "panel")
        with self.assertRaises(ValueError):
            index_unique([{"symbol": "", "market_date": "2026-07-22"}], "panel")


if __name__ == "__main__":
    unittest.main()
