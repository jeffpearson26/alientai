import unittest

from audit_russell_split_ratio_candidates import find_candidates, split_ratio_match


class RussellSplitRatioCandidateTests(unittest.TestCase):
    def test_identifies_split_and_reverse_split_shapes_without_classifying_them(self):
        self.assertEqual(split_ratio_match(0.5, factors=(2, 3), tolerance_pct=0.01), (2, "split_like"))
        self.assertEqual(split_ratio_match(3.0, factors=(2, 3), tolerance_pct=0.01), (3, "reverse_split_like"))

    def test_ignores_non_split_ratio_and_long_gap(self):
        candles = [
            {"date": "2026-01-02", "close": "10"},
            {"date": "2026-01-05", "close": "17"},
            {"date": "2026-06-02", "close": "34"},
        ]
        candidates, skipped = find_candidates("TEST", candles, factors=(2,), tolerance_pct=0.03, max_calendar_gap_days=5)
        self.assertEqual(candidates, [])
        self.assertEqual(skipped, 1)

    def test_preserves_exact_candidate_context(self):
        candles = [
            {"date": "2026-01-02", "close": "10"},
            {"date": "2026-01-05", "close": "5"},
        ]
        candidates, skipped = find_candidates("TEST", candles, factors=(2,), tolerance_pct=0.03, max_calendar_gap_days=5)
        self.assertEqual(skipped, 0)
        self.assertEqual(candidates[0]["candidate_type"], "split_like")
        self.assertEqual(candidates[0]["previous_date"], "2026-01-02")


if __name__ == "__main__":
    unittest.main()
