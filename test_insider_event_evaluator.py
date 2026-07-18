from __future__ import annotations

import unittest

from alientai_v2.research.insider_event_evaluator import evaluate_rows, select_event_rows


def row(day, visible, forward=1.0, **extra):
    value = {
        "symbol": "XYZ", "market_date": f"2026-01-{day:02d}",
        "insider_purchase_total_visible": visible,
        "insider_total_value_7d": 200_000,
        "label_forward_return_5d_pct": forward,
        "label_excess_return_5d_pct": forward - 0.5,
    }
    value.update(extra)
    return value


class InsiderEventEvaluatorTests(unittest.TestCase):
    def test_repeated_daily_visibility_creates_one_event(self):
        rows = [row(1, 0), row(2, 1), row(3, 1), row(4, 1)]
        events = select_event_rows(rows)
        self.assertEqual([item["market_date"] for item in events], ["2026-01-02"])

    def test_new_purchase_inside_horizon_is_suppressed(self):
        rows = [row(day, 0 if day == 1 else (1 if day < 4 else 2)) for day in range(1, 9)]
        self.assertEqual(len(select_event_rows(rows, horizon_trading_days=5)), 1)

    def test_new_purchase_after_horizon_is_kept(self):
        rows = [row(day, 0 if day == 1 else (1 if day < 7 else 2)) for day in range(1, 9)]
        self.assertEqual(len(select_event_rows(rows, horizon_trading_days=5)), 2)

    def test_summary_subtracts_cost_and_reports_buckets(self):
        result = evaluate_rows([row(1, 0), row(2, 1, forward=1.0)], round_trip_cost_pct=0.25)
        all_events = next(item for item in result["buckets"] if item["bucket"] == "all_events")
        self.assertEqual(all_events["sample_count"], 1)
        self.assertEqual(all_events["average_net_return_5d_pct"], 0.75)
        self.assertTrue(any(item["bucket"] == "value_100k_to_500k" for item in result["buckets"]))

    def test_future_total_cannot_backfill_earlier_row(self):
        events = select_event_rows([row(1, 0), row(2, 0), row(3, 1)])
        self.assertEqual(events[0]["market_date"], "2026-01-03")


if __name__ == "__main__":
    unittest.main()
