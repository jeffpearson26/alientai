from __future__ import annotations

import unittest

from train_v2_transformer_20day_sp500_from_supabase import validation_checkpoint_score


class TransformerCheckpointMetricTests(unittest.TestCase):
    def test_returns_net_metric_when_minimum_sample_is_met(self):
        metrics = {"thresholds": [{"threshold": 0.60, "predicted_positive_count": 800, "avg_selected_net_return_pct": 1.25}]}
        self.assertEqual(1.25, validation_checkpoint_score(metrics, 0.60, 500))

    def test_rejects_small_validation_sample(self):
        metrics = {"thresholds": [{"threshold": 0.60, "predicted_positive_count": 499, "avg_selected_net_return_pct": 9.0}]}
        self.assertIsNone(validation_checkpoint_score(metrics, 0.60, 500))

    def test_missing_threshold_fails_closed(self):
        self.assertIsNone(validation_checkpoint_score({"thresholds": []}, 0.60, 500))


if __name__ == "__main__":
    unittest.main()
