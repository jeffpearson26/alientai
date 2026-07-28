import unittest

import numpy as np

from train_evaluate_nasdaq_two_stage import score_methods, validation_choice


class NasdaqTwoStageTests(unittest.TestCase):
    def test_joint_score_requires_positive_expected_return(self):
        scores = score_methods(
            np.asarray([0.8, 0.5]), np.asarray([-2.0, 3.0])
        )
        self.assertEqual(scores["joint"].tolist(), [0.0, 1.5])

    def test_shape_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            score_methods(np.asarray([0.5]), np.asarray([1.0, 2.0]))

    def test_validation_selects_method_without_test_rows(self):
        rows = [
            {"label_forward_return_5d_pct": value}
            for value in (10.0, 9.0, -5.0, -4.0)
        ]
        scores = {
            "classifier": np.asarray([4.0, 3.0, 2.0, 1.0]),
            "expected_return": np.asarray([1.0, 2.0, 4.0, 3.0]),
            "joint": np.asarray([4.0, 6.0, 8.0, 3.0]),
        }
        winner, diagnostics = validation_choice(
            rows, scores, [0.5], minimum_signals=2, cost_pct=0.25
        )
        self.assertEqual(winner["method"], "classifier")
        self.assertEqual(len(diagnostics), 3)

    def test_minimum_signal_gate_fails_closed(self):
        rows = [{"label_forward_return_5d_pct": 1.0}] * 4
        scores = {name: np.arange(4, dtype=float) for name in (
            "classifier", "expected_return", "joint"
        )}
        with self.assertRaises(ValueError):
            validation_choice(rows, scores, [0.25], minimum_signals=3, cost_pct=0.25)

    def test_degenerate_tied_ranker_is_not_eligible(self):
        rows = [
            {"label_forward_return_5d_pct": value}
            for value in (5.0, 4.0, 3.0, 2.0, -1.0, -2.0, -3.0, -4.0)
        ]
        scores = {
            "classifier": np.arange(8, 0, -1, dtype=float),
            "expected_return": np.ones(8),
            "joint": np.arange(8, 0, -1, dtype=float),
        }
        winner, diagnostics = validation_choice(
            rows, scores, [0.5], minimum_signals=4, cost_pct=0.25
        )
        tied = next(row for row in diagnostics if row["method"] == "expected_return")
        self.assertEqual(tied["tie_expansion_ratio"], 2.0)
        self.assertNotEqual(winner["method"], "expected_return")


if __name__ == "__main__":
    unittest.main()
