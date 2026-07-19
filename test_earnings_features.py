from __future__ import annotations

import unittest

from alientai_v2.features.earnings_features import build_earnings_features


def event(available, surprise, surprise_pct, eligible=True):
    return {
        "ticker": "ABC", "available_at_utc": available,
        "reported_eps": 1.2, "estimated_eps": 1.0,
        "surprise": surprise, "surprise_percentage": surprise_pct,
        "is_training_eligible": eligible,
    }


class EarningsFeaturesTests(unittest.TestCase):
    def test_future_report_is_invisible(self):
        features = build_earnings_features(
            [event("2026-07-20T20:30:00Z", 0.2, 20)], "ABC", "2026-07-20T20:00:00Z"
        )
        self.assertFalse(features["earnings_available"])

    def test_quarantined_report_is_invisible(self):
        features = build_earnings_features(
            [event("2026-07-19T13:25:00Z", 0.2, 20, False)], "ABC", "2026-07-20T20:00:00Z"
        )
        self.assertFalse(features["earnings_available"])

    def test_latest_visible_event_and_windows(self):
        rows = [
            event("2026-04-01T13:25:00Z", 0.1, 10),
            event("2026-07-20T13:25:00Z", 0.2, 20),
        ]
        features = build_earnings_features(rows, "ABC", "2026-07-20T20:00:00Z")
        self.assertEqual(features["earnings_surprise_percentage"], 20.0)
        self.assertTrue(features["earnings_beat"])
        self.assertTrue(features["earnings_post_report_1d"])
        self.assertEqual(features["earnings_beat_streak"], 2)
        self.assertEqual(features["earnings_average_surprise_percentage_4q"], 15.0)

    def test_miss_breaks_beat_streak(self):
        rows = [event("2026-04-01T13:25:00Z", 0.2, 20), event("2026-07-01T13:25:00Z", -0.1, -10)]
        features = build_earnings_features(rows, "ABC", "2026-07-02T20:00:00Z")
        self.assertTrue(features["earnings_miss"])
        self.assertEqual(features["earnings_beat_streak"], 0)


if __name__ == "__main__":
    unittest.main()
