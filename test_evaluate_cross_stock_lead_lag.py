from __future__ import annotations

import unittest

import numpy as np

from evaluate_cross_stock_lead_lag import lagged_correlations


class CrossStockLeadLagTests(unittest.TestCase):
    def test_identifies_lagged_positive_relationship(self) -> None:
        values = np.asarray([[1.0, np.nan], [-1.0, 1.0], [2.0, -1.0], [-2.0, 2.0]])
        corr = lagged_correlations(values, lag=1, minimum_observations=3)
        self.assertAlmostEqual(float(corr[0, 1]), 1.0)

    def test_rejects_insufficient_overlap(self) -> None:
        values = np.asarray([[1.0, np.nan], [np.nan, 1.0], [2.0, np.nan]])
        corr = lagged_correlations(values, lag=1, minimum_observations=2)
        self.assertTrue(np.isnan(corr[0, 1]))


if __name__ == "__main__":
    unittest.main()
