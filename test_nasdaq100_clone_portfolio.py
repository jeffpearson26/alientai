import unittest

from evaluate_nasdaq100_clone_portfolio import select_validation_fraction, trade_metrics


class NasdaqPortfolioTests(unittest.TestCase):
    def test_cost_adjusted_metrics(self):
        rows = [
            {"label_forward_return_5d_pct": 1.25},
            {"label_forward_return_5d_pct": -0.75},
        ]
        result = trade_metrics(rows, 0.25)
        self.assertEqual(result["mean_net_return_pct"], 0.0)
        self.assertEqual(result["net_win_rate_pct"], 50.0)

    def test_fraction_is_selected_on_validation_net_return(self):
        rows = [
            {"technical_context_score": 0.99, "label_forward_return_5d_pct": -4.0},
            {"technical_context_score": 0.98, "label_forward_return_5d_pct": 8.0},
            {"technical_context_score": 0.97, "label_forward_return_5d_pct": 8.0},
            {"technical_context_score": 0.10, "label_forward_return_5d_pct": 0.0},
        ]
        fraction, cutoff, diagnostics = select_validation_fraction(
            rows, [0.25, 0.75], minimum_signals=1, cost_pct=0.25,
        )
        self.assertEqual(fraction, 0.75)
        self.assertGreater(cutoff, 0.10)
        self.assertEqual(len(diagnostics), 2)

    def test_selection_fails_closed_without_minimum_sample(self):
        rows = [{"technical_context_score": 0.9, "label_forward_return_5d_pct": 1.0}]
        with self.assertRaises(ValueError):
            select_validation_fraction(rows, [0.5], minimum_signals=2, cost_pct=0.25)

    def test_selection_rejects_positive_mean_with_negative_typical_trade(self):
        rows = [
            {"technical_context_score": 0.99, "label_forward_return_5d_pct": 20.0},
            {"technical_context_score": 0.98, "label_forward_return_5d_pct": -6.0},
            {"technical_context_score": 0.97, "label_forward_return_5d_pct": -6.0},
            {"technical_context_score": 0.96, "label_forward_return_5d_pct": -6.0},
        ]
        with self.assertRaisesRegex(ValueError, "locked quality gates"):
            select_validation_fraction(rows, [1.0], minimum_signals=4, cost_pct=0.25)


if __name__ == "__main__":
    unittest.main()
