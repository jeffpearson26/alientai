from __future__ import annotations

import unittest

from alientai_v2.research.rare_signal_gate import evaluate_rare_signal_gate


PASSING = {
    "signals": 40,
    "win_rate_after_cost": 0.60,
    "median_net_return_pct": 1.0,
    "mean_net_return_pct": 2.0,
    "fifth_percentile_net_return_pct": -5.0,
    "worst_trade_net_return_pct": -15.0,
    "approximate_cohort_max_drawdown_pct": -10.0,
    "largest_symbol_signal_share": 0.10,
}


class RareSignalGateTests(unittest.TestCase):
    def test_passing_metrics_require_every_check(self):
        result = evaluate_rare_signal_gate(PASSING)
        self.assertEqual("RESEARCH_PASS", result["status"])
        self.assertFalse(result["failure_reasons"])
        self.assertFalse(result["execution_enabled"])

    def test_negative_median_blocks_promotion(self):
        result = evaluate_rare_signal_gate({**PASSING, "median_net_return_pct": -0.01})
        self.assertEqual("RESEARCH_HOLD", result["status"])
        self.assertIn("positive typical outcome", result["failure_reasons"])

    def test_missing_tail_metric_fails_closed(self):
        metrics = dict(PASSING)
        metrics.pop("fifth_percentile_net_return_pct")
        result = evaluate_rare_signal_gate(metrics)
        self.assertEqual("RESEARCH_HOLD", result["status"])
        check = next(item for item in result["checks"] if item["name"] == "fifth-percentile tail")
        self.assertTrue(check["missing"])


if __name__ == "__main__":
    unittest.main()
