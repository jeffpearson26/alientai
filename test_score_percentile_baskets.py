from __future__ import annotations

import unittest

from evaluate_score_percentile_baskets import basket_report, percentile_edges


class ScorePercentileBasketTests(unittest.TestCase):
    def test_edges_are_frozen_from_validation_scores(self) -> None:
        edges = percentile_edges([0.0, 1.0, 2.0, 3.0], [0, 50, 100])
        self.assertEqual(edges, {0: 0.0, 50: 1.5, 100: 3.0})
        test_rows = [
            {"technical_context_score": 1.0, "label_forward_return_5d_pct": 1.0, "market_date": "2026-01-01", "future_market_date": "2026-01-02"},
            {"technical_context_score": 2.0, "label_forward_return_5d_pct": 2.0, "market_date": "2026-01-03", "future_market_date": "2026-01-04"},
        ]
        baskets = basket_report(test_rows, edges, [0, 50, 100], 0.0, 5, "label_forward_return_5d_pct")
        self.assertEqual(baskets[0]["signals"], 1)
        self.assertEqual(baskets[1]["signals"], 1)

    def test_capacity_is_applied_inside_each_basket(self) -> None:
        edges = {0: 0.0, 100: 1.0}
        rows = [
            {"technical_context_score": 0.9, "label_forward_return_5d_pct": 1.0,
             "market_date": "2026-01-01", "future_market_date": "2026-01-10"}
            for _ in range(6)
        ]
        baskets = basket_report(rows, edges, [0, 100], 0.0, 5, "label_forward_return_5d_pct")
        self.assertEqual(baskets[0]["candidates_before_capacity"], 6)
        self.assertEqual(baskets[0]["signals"], 5)


if __name__ == "__main__":
    unittest.main()
