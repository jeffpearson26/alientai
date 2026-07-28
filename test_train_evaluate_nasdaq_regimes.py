import unittest

from train_evaluate_nasdaq_regimes import choose_regime_candidate, qqq_regime


class NasdaqRegimeTests(unittest.TestCase):
    def test_regime_classification_is_deterministic(self):
        self.assertEqual(qqq_regime({
            "technical_benchmark_return_20d_pct": 1,
            "technical_benchmark_return_60d_pct": 2,
        }), "bullish")
        self.assertEqual(qqq_regime({
            "technical_benchmark_return_20d_pct": -1,
            "technical_benchmark_return_60d_pct": 0,
        }), "bearish")
        self.assertEqual(qqq_regime({
            "technical_benchmark_return_20d_pct": 1,
            "technical_benchmark_return_60d_pct": -2,
        }), "mixed")

    def test_validation_gate_requires_positive_typical_result(self):
        candidates = [{
            "regime": "bullish", "fraction": 0.01, "signals": 20,
            "mean_net_return_pct": 5.0, "median_net_return_pct": -1.0,
            "net_win_rate_pct": 60.0, "tie_expansion_ratio": 1.0,
        }]
        with self.assertRaises(ValueError):
            choose_regime_candidate(candidates, 15)

    def test_validation_selects_best_eligible_regime(self):
        common = {
            "fraction": 0.01, "signals": 20, "median_net_return_pct": 1.0,
            "net_win_rate_pct": 55.0, "tie_expansion_ratio": 1.0,
        }
        winner = choose_regime_candidate([
            {**common, "regime": "bullish", "mean_net_return_pct": 2.0},
            {**common, "regime": "mixed", "mean_net_return_pct": 1.0},
        ], 15)
        self.assertEqual(winner["regime"], "bullish")


if __name__ == "__main__":
    unittest.main()
