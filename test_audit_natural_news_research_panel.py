import unittest

from audit_natural_news_research_panel import audit_rows


class NaturalNewsPanelAuditTests(unittest.TestCase):
    def test_reports_complete_safe_coverage(self):
        report = audit_rows([
            {"symbol": "ABC", "as_of_utc": "2026-01-02T21:00:00+00:00", "news_available": True,
             "news_latest_published_utc": "2026-01-02T20:00:00+00:00"},
            {"symbol": "XYZ", "as_of_utc": "2026-01-03T21:00:00+00:00", "news_available": False,
             "news_missing_reason": "archive_response_missing"},
        ])
        self.assertEqual(report["rows"], 2)
        self.assertEqual(report["news_available_rows"], 1)
        self.assertEqual(report["coverage_pct"], 50.0)

    def test_future_visible_article_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "future_visible=1"):
            audit_rows([{"symbol": "ABC", "as_of_utc": "2026-01-02T21:00:00+00:00", "news_available": True,
                         "news_latest_published_utc": "2026-01-02T22:00:00+00:00"}])

    def test_duplicate_or_unexplained_missing_fails_closed(self):
        row = {"symbol": "ABC", "as_of_utc": "2026-01-02T21:00:00+00:00", "news_available": False,
               "news_missing_reason": "archive_response_missing"}
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit_rows([row, row])
        with self.assertRaisesRegex(ValueError, "malformed_missing=1"):
            audit_rows([{"symbol": "ABC", "as_of_utc": "2026-01-02T21:00:00+00:00", "news_available": False}])


if __name__ == "__main__":
    unittest.main()
