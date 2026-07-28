from __future__ import annotations

import unittest
from datetime import date, timedelta

from evaluate_unusual_call_60day_outcomes import compare_metrics, materialize_outcomes, metrics


class UnusualCallSixtyDayTests(unittest.TestCase):
    def test_requires_sixty_strictly_later_sessions(self) -> None:
        start = date(2026, 1, 5)
        path = {start: 100.0}
        for index in range(1, 60):
            path[start + timedelta(days=index)] = 100.0 + index
        base = [{"symbol": "AAA", "market_date": start.isoformat(), "close": 100.0}]
        options = [{"symbol": "AAA", "market_date": start.isoformat(), "option_call_volume": 10}]
        rows, coverage = materialize_outcomes(base, options, {"AAA": path})
        self.assertEqual(rows, [])
        self.assertEqual(coverage["incomplete_60_session_horizon"], 1)

    def test_reports_terminal_and_maximum_gain_separately(self) -> None:
        start = date(2026, 1, 5)
        path = {start: 100.0}
        for index in range(1, 61):
            path[start + timedelta(days=index)] = 130.0 if index == 30 else 110.0
        base = [{"symbol": "AAA", "market_date": start.isoformat(), "close": 100.0}]
        options = [{"symbol": "AAA", "market_date": start.isoformat(), "option_call_volume": 10}]
        rows, _ = materialize_outcomes(base, options, {"AAA": path})
        self.assertAlmostEqual(rows[0]["terminal_net_return_60d_pct"], 9.75)
        self.assertAlmostEqual(rows[0]["maximum_close_gain_within_60d_pct"], 30.0)
        result = metrics(rows)
        self.assertEqual(result["terminal_gain_at_least_20pct_rate_pct"], 0.0)
        self.assertEqual(result["reached_20pct_within_60d_rate_pct"], 100.0)

    def test_entry_must_match_stored_close(self) -> None:
        start = date(2026, 1, 5)
        path = {start + timedelta(days=index): 90.0 for index in range(61)}
        base = [{"symbol": "AAA", "market_date": start.isoformat(), "close": 100.0}]
        options = [{"symbol": "AAA", "market_date": start.isoformat(), "option_call_volume": 10}]
        rows, coverage = materialize_outcomes(base, options, {"AAA": path})
        self.assertEqual(rows, [])
        self.assertEqual(coverage["unresolved_entry_close"], 1)

    def test_comparison_reports_percentage_point_lift(self) -> None:
        natural = {
            "rows": 100, "mean_terminal_net_return_pct": 2.0,
            "terminal_net_win_rate_pct": 50.0,
        }
        unusual = {
            "rows": 20, "mean_terminal_net_return_pct": 3.0,
            "terminal_net_win_rate_pct": 55.0,
        }
        for threshold in (20, 30, 50):
            natural[f"terminal_gain_at_least_{threshold}pct_rate_pct"] = 10.0
            unusual[f"terminal_gain_at_least_{threshold}pct_rate_pct"] = 12.0
            natural[f"reached_{threshold}pct_within_60d_rate_pct"] = 20.0
            unusual[f"reached_{threshold}pct_within_60d_rate_pct"] = 23.0
        result = compare_metrics(natural, unusual)
        self.assertEqual(result["mean_terminal_net_return_lift_pct_points"], 1.0)
        self.assertEqual(result["reached_20pct_within_60d_rate_pct_lift_pct_points"], 3.0)


if __name__ == "__main__":
    unittest.main()
