from __future__ import annotations

import unittest

from evaluate_lead_lag_economic_value import choose_pretest_threshold, net_metrics


class LeadLagEconomicValueTests(unittest.TestCase):
    def test_cost_is_subtracted_from_directional_return(self):
        records = [{"source_residual_pct": 1.0, "target_open_to_close_pct": 1.0}]
        result = net_metrics(records, "same", 0.0, 0.25)
        self.assertEqual(1, result["signals"])
        self.assertEqual(0.75, result["mean_net_return_pct"])

    def test_opposite_direction_short_is_evaluated(self):
        records = [{"source_residual_pct": 1.0, "target_open_to_close_pct": -1.0}]
        result = net_metrics(records, "opposite", 0.0, 0.25)
        self.assertEqual(0.75, result["mean_net_return_pct"])

    def test_threshold_is_chosen_only_from_pretest_records(self):
        records = ([{"source_residual_pct": 0.3, "target_open_to_close_pct": 1.0} for _ in range(4)] + [{"source_residual_pct": 2.0, "target_open_to_close_pct": -1.0} for _ in range(4)])
        choice = choose_pretest_threshold(records, "same", 0.0, minimum_signals=2)
        self.assertIsNotNone(choice)
        self.assertEqual(0.0, choice[0])


if __name__ == "__main__":
    unittest.main()
