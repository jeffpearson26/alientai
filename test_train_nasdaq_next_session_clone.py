from __future__ import annotations

import unittest

from train_nasdaq_next_session_clone import (
    choose_policy,
    select_daily,
    split_dates,
)


class NasdaqNextSessionCloneTests(unittest.TestCase):
    def test_split_has_three_single_session_embargoes(self) -> None:
        dates = [f"2026-01-{day:02d}" for day in range(1, 101)]
        result = split_dates(dates)
        self.assertEqual(len(result["train_fit_embargo"]), 1)
        self.assertEqual(len(result["fit_policy_embargo"]), 1)
        self.assertEqual(len(result["policy_test_embargo"]), 1)
        used = [day for values in result.values() for day in values]
        self.assertEqual(len(used), len(set(used)))

    def test_daily_selection_caps_at_five(self) -> None:
        rows = [
            {
                "symbol": f"S{index}",
                "market_date": "2026-01-02",
                "label_forward_return_1d_pct": 1.0,
            }
            for index in range(10)
        ]
        selected = select_daily(rows, list(range(10)), cutoff=0.0)
        self.assertEqual(len(selected), 5)
        self.assertEqual(selected[0]["symbol"], "S9")

    def test_policy_requires_all_quality_checks(self) -> None:
        passing = {
            "signals": 20,
            "mean_net_return_pct": 0.1,
            "median_net_return_pct": 0.01,
            "win_rate_pct": 50.0,
            "tie_expansion_ratio": 1.0,
            "fraction": 0.01,
        }
        self.assertEqual(choose_policy([passing]), passing)
        self.assertIsNone(
            choose_policy([{**passing, "mean_net_return_pct": -0.01}])
        )


if __name__ == "__main__":
    unittest.main()
