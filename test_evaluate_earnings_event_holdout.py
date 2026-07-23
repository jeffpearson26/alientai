from __future__ import annotations

import unittest

from evaluate_earnings_event_holdout import evaluate


def row(day: str, count: int, surprise: float = 30.0, forward: float = 2.0):
    return {"symbol": "ABC", "market_date": day, "earnings_visible_quarter_count": count,
            "earnings_surprise_percentage": surprise, "earnings_beat_streak": 2,
            "label_forward_return_5d_pct": forward, "label_excess_return_5d_pct": forward}


class EarningsEventHoldoutTests(unittest.TestCase):
    def test_event_is_identified_using_prior_year_baseline_then_filtered(self) -> None:
        report = evaluate([row("2025-12-31", 1), row("2026-01-03", 2)], "2026", 5, 0.25)
        self.assertEqual(report["event_count"], 1)
        self.assertEqual(next(item for item in report["buckets"] if item["bucket"] == "all_events")["sample_count"], 1)


if __name__ == "__main__":
    unittest.main()
