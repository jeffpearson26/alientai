from __future__ import annotations

import unittest

from evaluate_context_portfolio import capacity_limited, split_chronologically


class ContextPortfolioTests(unittest.TestCase):
    def test_split_has_embargo_between_calibration_and_test(self):
        rows = [{"market_date": f"2026-01-{day:02d}"} for day in range(1, 11)]
        calibration, test = split_chronologically(rows, 0.6, 2)
        self.assertLess(max(row["market_date"] for row in calibration), min(row["market_date"] for row in test))
        self.assertEqual("2026-01-09", min(row["market_date"] for row in test))

    def test_capacity_prevents_overlapping_entries(self):
        rows = [
            {"market_date": "2026-01-01", "future_market_date": "2026-01-05", "technical_context_score": 0.9},
            {"market_date": "2026-01-02", "future_market_date": "2026-01-06", "technical_context_score": 0.8},
            {"market_date": "2026-01-06", "future_market_date": "2026-01-10", "technical_context_score": 0.7},
        ]
        self.assertEqual(["2026-01-01", "2026-01-06"], [row["market_date"] for row in capacity_limited(rows, 1)])


if __name__ == "__main__":
    unittest.main()
