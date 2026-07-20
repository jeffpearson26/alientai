from __future__ import annotations

import unittest

from train_matched_winner_premarket_ablation import (
    PREMARKET_FEATURES,
    join_feature_rows,
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

    def test_feature_families_exclude_future_labels(self):
        self.assertTrue(PREMARKET_FEATURES)
        self.assertTrue(technical_features())
        self.assertFalse(any(name.startswith("label_") for name in PREMARKET_FEATURES + technical_features()))

    def test_constant_and_missing_features_are_removed(self):
        rows = [{"a": 1, "b": None}, {"a": 1, "b": None}, {"a": 2, "b": None}]
        self.assertEqual(varying_features(rows, ["a", "b"]), ["a"])


if __name__ == "__main__":
    unittest.main()
