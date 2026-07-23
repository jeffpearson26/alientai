from __future__ import annotations

import unittest

from evaluate_insider_purchase_holdout import evaluate


class InsiderPurchaseHoldoutTests(unittest.TestCase):
    def test_uses_only_requested_holdout_year_and_available_rows(self) -> None:
        rows = [
            {"market_date": "2025-12-31", "label_forward_return_5d_pct": 99.0, "insider_purchase_available": True},
            {"market_date": "2026-01-02", "label_forward_return_5d_pct": 1.0, "insider_purchase_available": True, "insider_large_purchase_30d": True},
            {"market_date": "2026-01-03", "label_forward_return_5d_pct": -1.0, "insider_purchase_available": False, "insider_large_purchase_30d": True},
        ]
        report = evaluate(rows, "2026", 0.25)
        self.assertEqual(report["full_universe"]["signals"], 2)
        self.assertEqual(report["large_purchase_30d"]["signals"], 1)
        self.assertEqual(report["large_purchase_30d"]["median_net_return_pct"], 0.75)


if __name__ == "__main__":
    unittest.main()
