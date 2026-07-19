from __future__ import annotations

import unittest

from alientai_v2.research.earnings_event_evaluator import evaluate_rows, select_event_rows


def row(day, count, surprise=10.0, forward=2.0):
    return {
        "symbol": "ABC", "market_date": day,
        "earnings_visible_quarter_count": count,
        "earnings_surprise_percentage": surprise,
        "earnings_beat_streak": 2,
        "label_forward_return_5d_pct": forward,
        "label_excess_return_5d_pct": 1.0,
    }


class EarningsEventEvaluatorTests(unittest.TestCase):
    def test_repeated_visibility_creates_one_event(self):
        rows = [row("2026-01-01", 3), row("2026-01-02", 4), row("2026-01-03", 4)]
        self.assertEqual(len(select_event_rows(rows)), 1)

    def test_first_row_establishes_baseline(self):
        self.assertEqual(select_event_rows([row("2026-01-01", 4)]), [])

    def test_events_inside_horizon_are_suppressed(self):
        rows = [row("2026-01-01", 3), row("2026-01-02", 4), row("2026-01-03", 5)]
        self.assertEqual(len(select_event_rows(rows, 5)), 1)

    def test_summary_subtracts_cost_and_buckets_surprise(self):
        rows = [row("2026-01-01", 3), row("2026-01-02", 4, surprise=-5, forward=1.0)]
        report = evaluate_rows(rows, round_trip_cost_pct=0.25)
        buckets = {item["bucket"]: item for item in report["buckets"]}
        self.assertAlmostEqual(buckets["all_events"]["average_net_return_5d_pct"], 0.75)
        self.assertIn("eps_miss", buckets)
        self.assertFalse(report["execution_enabled"])


if __name__ == "__main__":
    unittest.main()
