from __future__ import annotations

import unittest

from alientai_v2.shadow_outcomes import build_due_outcomes


class ShadowOutcomeTests(unittest.TestCase):
    def signal(self, **overrides):
        row = {
            "signal_key": "2026-07-17|test|AAPL|BUY_CANDIDATE",
            "observed_at": "2026-07-17T08:00:00-07:00",
            "symbol": "AAPL",
            "engine_id": "test",
            "observed_price": 100.0,
            "prediction_horizon_days": 1.0,
        }
        row.update(overrides)
        return row

    def test_not_due_is_ignored(self):
        rows = build_due_outcomes([self.signal()], [{"symbol": "AAPL", "price": 110}], {}, "2026-07-17T09:00:00-07:00", set())
        self.assertEqual([], rows)

    def test_due_signal_records_cost_adjusted_return(self):
        rows = build_due_outcomes([self.signal()], [{"symbol": "AAPL", "price": 110}], {"shadow_signal_round_trip_cost_pct": 0.25}, "2026-07-18T08:01:00-07:00", set())
        self.assertEqual(10.0, rows[0]["raw_return_pct"])
        self.assertEqual(9.75, rows[0]["net_return_pct"])
        self.assertTrue(rows[0]["win_after_cost"])

    def test_scheduled_exit_takes_priority(self):
        signal = self.signal(scheduled_exit_time="2026-07-17T12:00:00-07:00", prediction_horizon_days=20)
        rows = build_due_outcomes([signal], [{"symbol": "AAPL", "price": 99}], {}, "2026-07-17T12:01:00-07:00", set())
        self.assertEqual(1, len(rows))

    def test_completed_signal_is_not_duplicated(self):
        signal = self.signal()
        rows = build_due_outcomes([signal], [{"symbol": "AAPL", "price": 110}], {}, "2026-07-18T09:00:00-07:00", {signal["signal_key"]})
        self.assertEqual([], rows)

    def test_missing_quote_is_deferred(self):
        rows = build_due_outcomes([self.signal()], [], {}, "2026-07-18T09:00:00-07:00", set())
        self.assertEqual([], rows)


if __name__ == "__main__":
    unittest.main()
