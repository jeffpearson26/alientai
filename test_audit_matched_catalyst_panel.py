import unittest

from audit_matched_catalyst_panel import audit


def row(**overrides):
    value = {
        "study_event_id": "event-1", "symbol": "AAA", "market_date": "2026-01-02", "study_role": "winner",
        "as_of_utc": "2026-01-02T20:00:00+00:00", "news_available": True,
        "news_latest_published_utc": "2026-01-02T19:00:00+00:00", "option_available": True, "option_chain_available": True,
    }
    value.update(overrides)
    return value


class MatchedCatalystPanelAuditTests(unittest.TestCase):
    def test_passes_complete_unique_point_in_time_rows(self):
        report = audit([row(), row(symbol="BBB", study_role="control")])
        self.assertTrue(report["audit_passes"])
        self.assertEqual(report["unique_symbol_market_dates"], 2)

    def test_flags_duplicate_and_future_news(self):
        report = audit([row(), row(news_latest_published_utc="2026-01-02T21:00:00+00:00")])
        self.assertFalse(report["audit_passes"])
        self.assertEqual(report["duplicate_row_keys"], 1)
        self.assertEqual(report["news_after_as_of_cutoff_rows"], 1)


if __name__ == "__main__":
    unittest.main()
