from __future__ import annotations

import unittest

import numpy as np

from train_matched_winner_lightgbm import event_balancing_weights, prepare_matrix, score_metrics


class MatchedWinnerLightGBMTests(unittest.TestCase):
    def test_event_controls_share_one_total_weight(self):
        rows = [
            {"study_event_id": "a", "study_role": "winner"},
            {"study_event_id": "a", "study_role": "control"},
            {"study_event_id": "a", "study_role": "control"},
        ]
        weights = event_balancing_weights(rows)
        self.assertEqual(weights.tolist(), [1.0, 0.5, 0.5])

    def test_future_label_is_rejected_as_feature(self):
        row = {"market_date": "2026-01-01", "study_label": 1, "label_forward_return_5d_pct": 10}
        with self.assertRaises(ValueError):
            prepare_matrix([row], ["label_forward_return_5d_pct"])

    def test_missing_indicator_is_explicit(self):
        rows = [
            {"market_date": "2026-01-01", "study_label": 1, "x": None},
            {"market_date": "2026-01-02", "study_label": 0, "x": 2.0},
        ]
        x, y, timestamps, names = prepare_matrix(rows, ["x"])
        self.assertEqual(names, ["x", "x__missing"])
        self.assertEqual(x[:, 1].tolist(), [1.0, 0.0])
        self.assertEqual(y.tolist(), [1, 0])
        self.assertLess(timestamps[0], timestamps[1])

    def test_extra_nonconstant_feature_is_eligible(self):
        rows = [{"x": 1.0}, {"x": 2.0}]
        from train_matched_winner_lightgbm import eligible_features
        self.assertIn("x", eligible_features(rows, ["x"]))

    def test_score_report_labels_case_control_precision(self):
        result = score_metrics(np.array([1, 0, 1, 0]), np.array([0.9, 0.8, 0.7, 0.1]))
        self.assertIn("matched_base_rate", result)
        self.assertIn("matched_set_precision", result["thresholds"][0])


if __name__ == "__main__":
    unittest.main()
