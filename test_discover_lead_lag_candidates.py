from __future__ import annotations

import unittest

from discover_lead_lag_candidates import rolling_pretest_correlations, stable_candidates


class LeadLagDiscoveryTests(unittest.TestCase):
    def test_finds_stable_one_session_lead(self):
        dates = [f"2024-01-{day:02d}" for day in range(1, 13)]
        market = {date: 0.0 for date in dates}
        source_values = [1, -2, 3, -4, 5, -6, 7, -8, 9, -10, 11, -12]
        source = dict(zip(dates, source_values))
        target = {dates[index]: (source_values[index - 1] if index else 0) for index in range(len(dates))}
        candidates = stable_candidates({"AAA": source, "BBB": target}, market, lags=(1,), min_samples=6, minimum_abs_correlation=0.5, alpha=1.0, rolling_windows=2)
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

    def test_sector_residualization_removes_shared_sector_motion(self):
        dates = [f"2024-03-{day:02d}" for day in range(1, 31)]
        market = {date: 0.0 for date in dates}
        sector_values = [((-1) ** index) * ((index % 9) + 1) for index in range(len(dates))]
        sector = dict(zip(dates, sector_values))
        source = dict(zip(dates, sector_values))
        target = {dates[index]: (sector_values[index - 1] if index else 0) for index in range(len(dates))}
        candidates = stable_candidates(
            {"AAA": source, "BBB": target}, market, lags=(1,), min_samples=15,
            minimum_abs_correlation=0.1, alpha=1.0,
            sector_returns={"XLK": sector}, sector_map={"AAA": "XLK", "BBB": "XLK"},
        )
        self.assertFalse(candidates)

    def test_sector_residualization_keeps_idiosyncratic_lead(self):
        dates = [f"2024-04-{day:02d}" for day in range(1, 31)]
        market = {date: 0.0 for date in dates}
        sector_values = [0.3 * ((-1) ** index) for index in range(len(dates))]
        sector = dict(zip(dates, sector_values))
        idiosyncratic = [((-1) ** index) * ((index % 7) + 2) for index in range(len(dates))]
        source = {date: sector_values[index] + idiosyncratic[index] for index, date in enumerate(dates)}
        target = {date: sector_values[index] + (idiosyncratic[index - 1] if index else 0) for index, date in enumerate(dates)}
        candidates = stable_candidates(
            {"AAA": source, "BBB": target}, market, lags=(1,), min_samples=15,
            minimum_abs_correlation=0.1, alpha=1.0,
            sector_returns={"XLK": sector}, sector_map={"AAA": "XLK", "BBB": "XLK"},
        )
        self.assertTrue(candidates)

    def test_missing_sector_mapping_fails_closed_by_skipping_pair(self):
        dates = [f"2024-05-{day:02d}" for day in range(1, 16)]
        market = {date: 0.0 for date in dates}
        values = dict(zip(dates, range(len(dates))))
        candidates = stable_candidates(
            {"AAA": values, "BBB": values}, market, lags=(1,), min_samples=6,
            sector_returns={"XLK": values}, sector_map={"AAA": "XLK"}, alpha=1.0,
        )
        self.assertEqual([], candidates)

    def test_rolling_pretest_windows_do_not_include_held_out_data(self):
        samples = [(str(index), float(index), float(index), 0.0) for index in range(18)]
        # The final six observations are deliberately unrelated; they must not
        # influence the pre-test rolling correlation calculation.
        samples[-1] = ("17", 17.0, -17.0, 0.0)
        values = rolling_pretest_correlations(samples, windows=3)
        self.assertEqual(3, len(values))
        self.assertTrue(all(value > 0.99 for value in values))


if __name__ == "__main__":
    unittest.main()
