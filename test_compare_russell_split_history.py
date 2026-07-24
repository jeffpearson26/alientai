import unittest

from compare_russell_split_history import reconcile


class RussellSplitHistoryComparisonTests(unittest.TestCase):
    def test_matches_date_and_ratio(self):
        report = reconcile(
            [{"symbol": "AAA", "current_date": "2026-01-05", "price_ratio": 0.5}],
            {"AAA": [{"effective_date": "2026-01-05", "split_factor": "0.5"}]},
            date_tolerance_days=3,
            ratio_tolerance_pct=0.10,
        )
        self.assertEqual(report["counts"]["date_and_ratio_match"], 1)

    def test_preserves_date_only_and_unmatched_findings(self):
        report = reconcile(
            [
                {"symbol": "AAA", "current_date": "2026-01-05", "price_ratio": 0.7},
                {"symbol": "BBB", "current_date": "2026-01-05", "price_ratio": 0.5},
            ],
            {"AAA": [{"effective_date": "2026-01-06", "split_factor": "0.5"}]},
            date_tolerance_days=3,
            ratio_tolerance_pct=0.10,
        )
        self.assertEqual(report["counts"]["date_only_match"], 1)
        self.assertEqual(report["counts"]["missing_provider_symbol"], 1)


if __name__ == "__main__":
    unittest.main()
