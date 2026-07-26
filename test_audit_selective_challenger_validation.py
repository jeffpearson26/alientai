from __future__ import annotations

import unittest

import numpy as np

from audit_selective_challenger_validation import binary_auc, ranked_slices


class SelectiveChallengerValidationAuditTests(unittest.TestCase):
    def test_auc_is_one_for_perfect_ranking(self):
        self.assertEqual(
            1.0,
            binary_auc(
                np.asarray([0, 0, 1, 1]),
                np.asarray([0.1, 0.2, 0.8, 0.9]),
            ),
        )

    def test_auc_handles_ties_and_single_class(self):
        self.assertEqual(
            0.5,
            binary_auc(np.asarray([0, 1]), np.asarray([0.5, 0.5])),
        )
        self.assertIsNone(binary_auc(np.asarray([1, 1]), np.asarray([0.5, 0.6])))

    def test_ranked_slices_use_highest_scores(self):
        rows = ranked_slices(
            np.asarray([0.1, 0.9, 0.8, 0.2]),
            np.asarray([0, 1, 1, 0]),
            np.asarray([-1.0, 3.0, 2.0, -2.0]),
            fractions=(0.5,),
        )
        self.assertEqual(2, rows[0]["rows"])
        self.assertEqual(1.0, rows[0]["positive_rate"])
        self.assertEqual(2.5, rows[0]["mean_net_return_pct"])


if __name__ == "__main__":
    unittest.main()
