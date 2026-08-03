import unittest

from evaluate_nasdaq100_clone_portfolio import select_validation_fraction


class NasdaqClonePortfolioTests(unittest.TestCase):
    def rows(self, scores):
        return [
            {
                "symbol": f"S{index}",
                "market_date": f"2026-01-{index + 1:02d}",
                "future_market_date": f"2026-02-{index + 1:02d}",
                "technical_context_score": score,
                "label_forward_return_5d_pct": 1.0,
            }
            for index, score in enumerate(scores)
        ]

    def test_rejects_cutoff_expanded_by_tied_scores(self):
        with self.assertRaisesRegex(ValueError, "no validation fraction"):
            select_validation_fraction(
                self.rows([0.9] * 10 + [0.1] * 10),
                fractions=[0.05],
                minimum_signals=1,
                cost_pct=0.25,
                maximum_tie_expansion_ratio=1.5,
            )

    def test_accepts_distinct_scores_without_tie_expansion(self):
        fraction, cutoff, diagnostics = select_validation_fraction(
            self.rows([float(value) for value in range(20)]),
            fractions=[0.10],
            minimum_signals=1,
            cost_pct=0.25,
            maximum_tie_expansion_ratio=1.5,
        )
        self.assertEqual(fraction, 0.10)
        self.assertEqual(diagnostics[0]["intended_signals"], 2)
        self.assertEqual(diagnostics[0]["candidates_before_capacity"], 2)
        self.assertEqual(diagnostics[0]["tie_expansion_ratio"], 1.0)
        self.assertGreater(cutoff, 0)


if __name__ == "__main__":
    unittest.main()
