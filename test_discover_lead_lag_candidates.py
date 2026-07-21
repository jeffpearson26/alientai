from __future__ import annotations

import unittest

from discover_lead_lag_candidates import stable_candidates


class LeadLagDiscoveryTests(unittest.TestCase):
    def test_finds_stable_one_session_lead(self):
        dates = [f"2024-01-{day:02d}" for day in range(1, 13)]
        market = {date: 0.0 for date in dates}
        source_values = [1, -2, 3, -4, 5, -6, 7, -8, 9, -10, 11, -12]
        source = dict(zip(dates, source_values))
        target = {dates[index]: (source_values[index - 1] if index else 0) for index in range(len(dates))}
        candidates = stable_candidates({"AAA": source, "BBB": target}, market, lags=(1,), min_samples=6, minimum_abs_correlation=0.5, alpha=1.0)
        self.assertTrue(any(
            row["source_symbol"] == "AAA" and row["target_symbol"] == "BBB" and row["lag_sessions"] == 1
            for row in candidates
        ))

    def test_reports_but_does_not_select_on_held_out_direction(self):
        dates = [f"2024-02-{day:02d}" for day in range(1, 31)]
        market = {date: 0.0 for date in dates}
        source_values = [((-1) ** index) * ((index % 7) + 1) for index in range(len(dates))]
        source = dict(zip(dates, source_values))
        target_values = [0]
        for index in range(1, len(dates)):
            sign = 1 if index <= 18 else -1
            target_values.append(sign * source_values[index - 1])
        target = dict(zip(dates, target_values))
        candidates = stable_candidates({"AAA": source, "BBB": target}, market, lags=(1,), min_samples=15, minimum_abs_correlation=0.1, alpha=1.0)
        candidate = next(row for row in candidates if row["source_symbol"] == "AAA" and row["target_symbol"] == "BBB")
        self.assertLess(candidate["held_out_test_p_value"], 1.0)
        self.assertLess(candidate["test_residual_correlation"], 0)


if __name__ == "__main__":
    unittest.main()
