from __future__ import annotations

import unittest

import numpy as np

from evaluate_matched_winner_full_universe import (
    apply_calibration,
    build_matrix,
    max_drawdown,
    non_overlapping,
    quantile_calibration,
)


class MatchedWinnerFullUniverseTests(unittest.TestCase):
    def test_future_label_feature_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "future outcome"):
            build_matrix([{"label_forward_return_5d_pct": 12.0}], ["label_forward_return_5d_pct"])

    def test_model_missing_indicator_is_recreated(self):
        matrix = build_matrix([{"alpha": None}, {"alpha": 2.0}], ["alpha", "alpha__missing"])
        self.assertEqual(matrix.tolist(), [[0.0, 1.0], [2.0, 0.0]])

    def test_calibration_is_monotonic(self):
        scores = np.arange(8, dtype=float)
        labels = np.asarray([0, 1, 0, 0, 1, 1, 0, 1])
        bins = quantile_calibration(scores, labels, bin_count=4)
        values = [row["empirical_probability"] for row in bins]
        self.assertEqual(values, sorted(values))
        calibrated = apply_calibration(np.asarray([0.0, 7.0]), bins)
        self.assertLessEqual(calibrated[0], calibrated[1])

    def test_non_overlapping_is_per_symbol(self):
        rows = [
            {"symbol": "A", "market_date": "2026-01-01", "raw_score": 0.9},
            {"symbol": "A", "market_date": "2026-01-03", "raw_score": 0.8},
            {"symbol": "B", "market_date": "2026-01-03", "raw_score": 0.7},
            {"symbol": "A", "market_date": "2026-01-08", "raw_score": 0.6},
        ]
        chosen = non_overlapping(rows, hold_calendar_days=7)
        self.assertEqual([(row["symbol"], row["market_date"]) for row in chosen], [
            ("A", "2026-01-01"), ("B", "2026-01-03"), ("A", "2026-01-08"),
        ])

    def test_drawdown_uses_compounded_equity(self):
        self.assertAlmostEqual(max_drawdown([10.0, -10.0]), -10.0)


if __name__ == "__main__":
    unittest.main()
