from __future__ import annotations

import unittest

from evaluate_premarket_ablation_natural_universe import natural_promotion_gate


def slice_(selection, mean=1.0, median=0.5, rate=0.1, drawdown=-10.0, signals=40):
    return {
        "selection": selection, "signals": signals, "exceptional_winner_rate": rate,
        "mean_net_return_pct": mean, "median_net_return_pct": median,
        "approximate_cohort_max_drawdown_pct": drawdown,
    }


class PremarketNaturalUniverseEvaluationTests(unittest.TestCase):
    def test_pass_requires_at_least_one_complete_natural_slice(self):
        names = ("top_0.0010", "top_0.0025", "top_0.0050", "top_0.0100")
        baseline = [slice_(name, mean=0.2, median=-0.1, rate=0.05, drawdown=-12) for name in names]
        combined = [slice_(name, mean=0.5, median=0.1, rate=0.08, drawdown=-9) for name in names]
        result = natural_promotion_gate([
            {"name": "technical_only", "test_slices": baseline},
            {"name": "technical_plus_premarket", "test_slices": combined},
        ])
        self.assertEqual(result["status"], "NATURAL_UNIVERSE_PASS")
        self.assertFalse(result["execution_enabled"])

    def test_gate_holds_when_combined_drawdown_is_worse(self):
        baseline = [slice_("top_0.0010", drawdown=-10)]
        combined = [slice_("top_0.0010", mean=2, median=1, rate=0.2, drawdown=-20)]
        result = natural_promotion_gate([
            {"name": "technical_only", "test_slices": baseline},
            {"name": "technical_plus_premarket", "test_slices": combined},
        ])
        self.assertEqual(result["status"], "NATURAL_UNIVERSE_HOLD")

    def test_gate_fails_closed_without_models(self):
        self.assertEqual(natural_promotion_gate([])["status"], "NATURAL_UNIVERSE_HOLD")


if __name__ == "__main__":
    unittest.main()
