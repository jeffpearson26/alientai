from __future__ import annotations

import unittest

from train_ai_semi_intraday_next_session_clone import (
    choose_policy,
    passes_quality_gate,
    select_daily,
    split_dates,
)


class AiSemiIntradayNextSessionCloneTests(unittest.TestCase):
    def test_split_preserves_three_embargo_dates(self) -> None:
        dates = [f"D{index:03d}" for index in range(100)]
        split = split_dates(dates)
        self.assertEqual(len(split["train_fit_embargo"]), 1)
        self.assertEqual(len(split["fit_policy_embargo"]), 1)
        self.assertEqual(len(split["policy_test_embargo"]), 1)

    def test_daily_fraction_and_maximum_are_both_enforced(self) -> None:
        rows = [
            {
                "symbol": f"S{index:02d}",
                "market_date": "D001",
                "label_next_complete_session_close_net_pct": 1.0,
            }
            for index in range(17)
        ]
        self.assertEqual(len(select_daily(rows, range(17), 0.10)), 2)
        self.assertEqual(len(select_daily(rows, range(17), 0.50)), 5)

    def test_policy_gate_rejects_small_or_bad_samples(self) -> None:
        passing = {
            "fraction": 0.1,
            "signals": 30,
            "decision_dates": 10,
            "mean_net_return_pct": 0.1,
            "median_net_return_pct": 0.1,
            "win_rate_pct": 50.0,
            "fifth_percentile_net_return_pct": -5.0,
        }
        self.assertEqual(choose_policy([passing]), passing)
        self.assertIsNone(choose_policy([{**passing, "signals": 29}]))
        self.assertIsNone(
            choose_policy([{**passing, "mean_net_return_pct": -0.1}])
        )
        self.assertTrue(passes_quality_gate(passing))
        self.assertFalse(
            passes_quality_gate({**passing, "win_rate_pct": 49.99})
        )


if __name__ == "__main__":
    unittest.main()
