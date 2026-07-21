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
        candidates = stable_candidates({"AAA": source, "BBB": target}, market, lags=(1,), min_samples=6, minimum_abs_correlation=0.5, train_fraction=0.6)
        self.assertTrue(any(
            row["source_symbol"] == "AAA" and row["target_symbol"] == "BBB" and row["lag_sessions"] == 1
            for row in candidates
        ))

    def test_rejects_direction_that_changes_out_of_sample(self):
        dates = [f"2024-02-{day:02d}" for day in range(1, 13)]
        market = {date: 0.0 for date in dates}
        source_values = [1, -2, 4, -8, 16, -32, 64, -128, 256, -512, 1024, -2048]
        source = dict(zip(dates, source_values))
        target_values = [0]
        for index in range(1, len(dates)):
            sign = 1 if index <= 6 else -1
            target_values.append(sign * source_values[index - 1])
        target = dict(zip(dates, target_values))
        candidates = stable_candidates({"AAA": source, "BBB": target}, market, lags=(1,), min_samples=6, minimum_abs_correlation=0.1, train_fraction=0.6)
        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
