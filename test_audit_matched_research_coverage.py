from __future__ import annotations

import unittest

from audit_matched_research_coverage import coverage_summary, cutoff_violations


class MatchedResearchCoverageTests(unittest.TestCase):
    def test_cutoff_flags_late_or_invalid_timestamps(self):
        rows = [
            {"premarket_available": True, "premarket_last_timestamp_et": "2024-01-02 09:25:00"},
            {"premarket_available": True, "premarket_last_timestamp_et": "2024-01-02 09:30:00"},
            {"premarket_available": True, "premarket_last_timestamp_et": "not-a-date"},
            {"premarket_available": False},
        ]
        self.assertEqual(cutoff_violations(rows), 2)

    def test_complete_matched_rows_pass(self):
        base = [
            {"study_event_id": "a", "symbol": "AAA", "market_date": "2024-01-02", "study_role": "winner"},
            {"study_event_id": "a", "symbol": "BBB", "market_date": "2024-01-02", "study_role": "control"},
        ]
        features = [
            {**base[0], "premarket_available": True, "premarket_last_timestamp_et": "2024-01-02 09:25:00"},
            {**base[1], "premarket_available": False},
        ]
        labels = [
            {**base[0], "premarket_label_available": True},
            {**base[1], "premarket_label_available": True},
        ]
        result = coverage_summary(base, features, labels, [], [])
        self.assertTrue(result["audit_passes"])
        self.assertEqual(result["premarket_features"]["available_pct"], 50.0)
        self.assertEqual(result["open_entry_labels"]["missing_base_rows"], 0)

    def test_missing_or_duplicate_rows_fail_audit(self):
        base = [
            {"study_event_id": "a", "symbol": "AAA", "market_date": "2024-01-02", "study_role": "winner"},
            {"study_event_id": "b", "symbol": "BBB", "market_date": "2024-01-02", "study_role": "control"},
        ]
        features = [
            {**base[0], "premarket_available": True, "premarket_last_timestamp_et": "2024-01-02 09:30:00"},
            {**base[0], "premarket_available": False},
        ]
        labels = [{**base[0], "premarket_label_available": True}]
        result = coverage_summary(base, features, labels, [], [])
        self.assertFalse(result["audit_passes"])
        self.assertEqual(result["premarket_features"]["row_key_duplicates"], 1)
        self.assertEqual(result["premarket_features"]["cutoff_violations"], 1)


if __name__ == "__main__":
    unittest.main()
