from __future__ import annotations

import unittest

import numpy as np

from train_matched_winner_premarket_ablation import (
    PREMARKET_FEATURES,
    join_feature_rows,
    join_open_entry_labels,
    promotion_gate,
    ranked_return_slices,
    technical_features,
    varying_features,
)


class MatchedWinnerPremarketAblationTests(unittest.TestCase):
    def test_join_requires_full_event_identity(self):
        base = [
            {"study_event_id": "e", "study_role": "winner", "symbol": "AAA", "market_date": "2024-01-02"},
            {"study_event_id": "e", "study_role": "control", "symbol": "BBB", "market_date": "2024-01-02"},
        ]
        features = [{
            "study_event_id": "e", "study_role": "control", "symbol": "BBB", "market_date": "2024-01-02",
            "premarket_available": True, "premarket_gap_pct": 5.0,
        }]
        joined, coverage = join_feature_rows(base, features)
        self.assertIsNone(joined[0]["premarket_gap_pct"])
        self.assertEqual(joined[1]["premarket_gap_pct"], 5.0)
        self.assertEqual(coverage["matched_feature_rows"], 1)
        self.assertEqual(coverage["premarket_available_rows"], 1)

    def test_duplicate_feature_identity_fails_closed(self):
        feature = {"study_event_id": "e", "study_role": "winner", "symbol": "AAA", "market_date": "2024-01-02"}
        with self.assertRaises(ValueError):
            join_feature_rows([], [feature, feature])

    def test_open_entry_labels_replace_ex_post_daily_case_label(self):
        base = [{
            "study_event_id": "e", "study_role": "winner", "symbol": "AAA",
            "market_date": "2024-01-02", "study_label": 1, "label_forward_return_5d_pct": 12.0,
        }]
        labels = [{
            "study_event_id": "e", "study_role": "winner", "symbol": "AAA", "market_date": "2024-01-02",
            "premarket_label_available": True, "premarket_label_exceptional_winner": False,
            "premarket_forward_return_5d_pct": 2.0, "premarket_entry_price": 100, "premarket_exit_price": 102,
        }]
        joined, coverage = join_open_entry_labels(base, labels)
        self.assertEqual(joined[0]["study_label"], 0)
        self.assertEqual(joined[0]["label_forward_return_5d_pct"], 2.0)
        self.assertEqual(coverage["tradable_label_rows"], 1)

    def test_missing_open_entry_label_is_excluded_not_negative(self):
        base = [{"study_event_id": "e", "study_role": "winner", "symbol": "AAA", "market_date": "2024-01-02"}]
        joined, coverage = join_open_entry_labels(base, [])
        self.assertEqual(joined, [])
        self.assertEqual(coverage["tradable_label_rows"], 0)

    def test_feature_families_exclude_future_labels(self):
        self.assertTrue(PREMARKET_FEATURES)
        self.assertTrue(technical_features())
        self.assertFalse(any(name.startswith("label_") for name in PREMARKET_FEATURES + technical_features()))

    def test_constant_and_missing_features_are_removed(self):
        rows = [{"a": 1, "b": None}, {"a": 1, "b": None}, {"a": 2, "b": None}]
        self.assertEqual(varying_features(rows, ["a", "b"]), ["a"])

    def test_return_slices_subtract_cost_and_rank_by_score(self):
        rows = [
            {"symbol": "A", "study_label": 1, "label_forward_return_5d_pct": 10.0},
            {"symbol": "B", "study_label": 0, "label_forward_return_5d_pct": -2.0},
            {"symbol": "C", "study_label": 0, "label_forward_return_5d_pct": 1.0},
        ]
        result = ranked_return_slices(rows, np.asarray([0, 1, 2]), np.asarray([0.9, 0.1, 0.2]), 0.25)
        self.assertEqual(result[0]["signals"], 1)
        self.assertEqual(result[0]["mean_net_return_pct"], 9.75)
        self.assertEqual(result[0]["exceptional_winner_rate"], 1.0)

    def test_return_slices_require_aligned_scores(self):
        with self.assertRaises(ValueError):
            ranked_return_slices([], np.asarray([0]), np.asarray([]), 0.25)

    def test_promotion_gate_requires_validation_and_test_improvement(self):
        baseline_slice = {
            "fraction": 0.01, "signals": 40, "exceptional_winner_rate": 0.10,
            "mean_net_return_pct": 0.2, "median_net_return_pct": -0.1,
            "fifth_percentile_net_return_pct": -5.0,
        }
        combined_slice = {
            "fraction": 0.01, "signals": 40, "exceptional_winner_rate": 0.15,
            "mean_net_return_pct": 0.5, "median_net_return_pct": 0.1,
            "fifth_percentile_net_return_pct": -4.0,
        }
        experiments = [
            {"name": "technical_only", "validation_return_slices": [baseline_slice], "test_return_slices": [baseline_slice]},
            {"name": "technical_plus_premarket", "validation_return_slices": [combined_slice], "test_return_slices": [combined_slice]},
        ]
        self.assertEqual(promotion_gate(experiments)["status"], "RESEARCH_PASS")
        experiments[1]["test_return_slices"][0] = {**combined_slice, "median_net_return_pct": -0.01}
        self.assertEqual(promotion_gate(experiments)["status"], "RESEARCH_HOLD")

    def test_promotion_gate_fails_closed_when_slice_missing(self):
        result = promotion_gate([])
        self.assertEqual(result["status"], "RESEARCH_HOLD")
        self.assertFalse(result["execution_enabled"])


if __name__ == "__main__":
    unittest.main()
