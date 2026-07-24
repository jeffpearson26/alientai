import unittest

from build_natural_news_research_panel import join_panel


class NaturalNewsResearchPanelTests(unittest.TestCase):
    def test_exact_join_preserves_base_and_news_features(self):
        base = [{"symbol": "ABC", "as_of_utc": "2026-01-02T21:00:00+00:00", "market_date": "2026-01-02", "label_up_2pct": True}]
        news = [{"symbol": "ABC", "as_of_utc": "2026-01-02T21:00:00+00:00", "news_available": True, "news_article_count": 3, "source": "test"}]
        row = join_panel(base, news)[0]
        self.assertTrue(row["label_up_2pct"])
        self.assertTrue(row["news_available"])
        self.assertEqual(row["news_article_count"], 3)
        self.assertEqual(row["news_source"], "test")

    def test_missing_news_stays_explicitly_missing(self):
        base = [{"symbol": "ABC", "as_of_utc": "2026-01-02T21:00:00+00:00"}]
        row = join_panel(base, [])[0]
        self.assertFalse(row["news_available"])
        self.assertEqual(row["news_missing_reason"], "archive_response_missing")

    def test_extra_or_duplicate_news_fails_closed(self):
        base = [{"symbol": "ABC", "as_of_utc": "2026-01-02T21:00:00+00:00"}]
        extra = [{"symbol": "XYZ", "as_of_utc": "2026-01-02T21:00:00+00:00", "news_available": True}]
        with self.assertRaisesRegex(ValueError, "absent from base"):
            join_panel(base, extra)
        duplicate = [
            {"symbol": "ABC", "as_of_utc": "2026-01-02T21:00:00+00:00", "news_available": True},
            {"symbol": "ABC", "as_of_utc": "2026-01-02T21:00:00+00:00", "news_available": True},
        ]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            join_panel(base, duplicate)


if __name__ == "__main__":
    unittest.main()
