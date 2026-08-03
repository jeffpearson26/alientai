import unittest

from build_ai_semiconductor_earnings_context import attach_earnings, visible_earnings_features


class EarningsContextTests(unittest.TestCase):
    def test_future_event_is_excluded(self):
        events = [
            {
                "available_at_utc": "2026-01-02T21:30:00Z",
                "surprise_percentage": 10,
                "is_training_eligible": True,
            }
        ]
        result = visible_earnings_features(events, "2026-01-02T21:00:00Z")
        self.assertFalse(result["narrative_earnings_available"])

    def test_latest_visible_event_and_streak_are_used(self):
        events = [
            {
                "available_at_utc": "2025-10-01T20:30:00Z",
                "surprise_percentage": 5,
                "is_training_eligible": True,
            },
            {
                "available_at_utc": "2026-01-01T20:30:00Z",
                "surprise_percentage": 10,
                "is_training_eligible": True,
            },
        ]
        result = visible_earnings_features(events, "2026-01-03T20:30:00Z")
        self.assertEqual(result["narrative_fund_eps_surprise_pct"], 10)
        self.assertEqual(result["narrative_fund_eps_beat_streak"], 2)
        self.assertEqual(result["narrative_fund_eps_miss_streak"], 0)
        self.assertEqual(result["narrative_fund_days_since_report"], 2)

    def test_panel_requires_unique_keys(self):
        rows = [{"symbol": "AMD", "market_date": "2026-01-02", "as_of_utc": "2026-01-02T21:00:00Z"}] * 2
        with self.assertRaises(ValueError):
            attach_earnings(rows, [])


if __name__ == "__main__":
    unittest.main()
