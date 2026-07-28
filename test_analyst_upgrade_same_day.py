from __future__ import annotations

import unittest

from evaluate_analyst_upgrade_same_day import evaluate_events, event_session


class AnalystUpgradeSameDayTests(unittest.TestCase):
    def test_classifies_announcement_in_eastern_time(self) -> None:
        self.assertEqual(event_session("2026-07-20T12:00:00Z")[1], "premarket")
        self.assertEqual(event_session("2026-07-20T15:00:00Z")[1], "intraday")
        self.assertEqual(event_session("2026-07-20T21:00:00Z")[1], "afterhours")

    def test_requires_exact_old_and_new_labels(self) -> None:
        events = [
            {
                "ticker": "AAA", "old_rating": "Hold", "new_rating": "Buy",
                "announcement_timestamp_utc": "2026-07-20T12:00:00Z",
            },
            {
                "ticker": "AAA", "old_rating": "Neutral", "new_rating": "Buy",
                "announcement_timestamp_utc": "2026-07-20T12:00:00Z",
            },
        ]
        history = {
            "AAA": [
                {"date": "2026-07-17", "open": 99.0, "close": 100.0},
                {"date": "2026-07-20", "open": 102.0, "close": 104.0},
            ]
        }
        result = evaluate_events(events, history, "Hold", "Buy")
        self.assertEqual(result["exact_event_count"], 1)
        self.assertEqual(result["unique_premarket_symbol_days_with_prices"], 1)
        self.assertAlmostEqual(result["opening_gap"]["mean_pct"], 2.0)
        self.assertAlmostEqual(result["open_to_close"]["mean_pct"], 100 * (104 / 102 - 1))

    def test_intraday_event_is_not_used_for_open_to_close_reaction(self) -> None:
        events = [{
            "ticker": "AAA", "old_rating": "Hold", "new_rating": "Buy",
            "announcement_timestamp_utc": "2026-07-20T15:00:00Z",
        }]
        result = evaluate_events(events, {}, "Hold", "Buy")
        self.assertEqual(result["announcement_sessions"]["intraday"], 1)
        self.assertEqual(result["open_to_close"]["rows"], 0)


if __name__ == "__main__":
    unittest.main()
