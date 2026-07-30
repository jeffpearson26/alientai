from __future__ import annotations

import unittest

from build_nasdaq_news_options_panel import build_panel


class NasdaqNewsOptionsPanelTests(unittest.TestCase):
    def test_builds_numeric_prefixed_features(self) -> None:
        base = [{"symbol": "AAA", "market_date": "2026-01-01", "option_call_volume": 12}]
        news = [{"symbol": "AAA", "as_of_utc": "2026-01-01T21:00:00+00:00", "news_available": True, "news_weighted_sentiment": "0.5"}]
        calls = [{"symbol": "AAA", "market_date": "2026-01-01", "call_volume_unusual": True, "call_volume_zscore": 3.2}]
        row = build_panel(base, news, calls)[0]
        self.assertEqual(row["model_news_weighted_sentiment"], 0.5)
        self.assertEqual(row["model_call_volume_unusual"], 1.0)
        self.assertEqual(row["model_option_call_volume"], 12.0)

    def test_rejects_missing_exact_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "exact news"):
            build_panel([{"symbol": "AAA", "market_date": "2026-01-01"}], [], [])


if __name__ == "__main__":
    unittest.main()
