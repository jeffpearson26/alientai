from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from alientai_v2.features.insider_purchase_features import build_insider_purchase_features, visible_purchases


NOW = datetime(2026, 7, 18, 16, tzinfo=timezone.utc)


def purchase(name, days_ago, value=100_000, **extra):
    row = {
        "ticker": "XYZ", "insider_name": name, "transaction_code": "P",
        "transaction_date": (NOW - timedelta(days=days_ago + 1)).date().isoformat(),
        "available_at_utc": (NOW - timedelta(days=days_ago)).isoformat(),
        "shares": 100, "price": value / 100, "total_value": value,
        "ownership_type": "D", "shares_owned_after": 1100,
        "is_training_eligible": True,
    }
    row.update(extra)
    return row


class InsiderPurchaseFeatureTests(unittest.TestCase):
    def test_future_filing_is_invisible(self):
        future = purchase("A", -1)
        self.assertEqual(visible_purchases([future], "XYZ", NOW), [])

    def test_quarantined_row_is_invisible(self):
        bad = purchase("A", 1, is_training_eligible=False)
        self.assertEqual(visible_purchases([bad], "XYZ", NOW), [])

    def test_amendment_like_duplicate_counts_once(self):
        original = purchase("A", 3)
        amendment = dict(original, available_at_utc=(NOW - timedelta(days=2)).isoformat(), is_amendment=True)
        self.assertEqual(len(visible_purchases([original, amendment], "XYZ", NOW)), 1)

    def test_cluster_buying_requires_two_unique_insiders(self):
        result = build_insider_purchase_features([purchase("A", 2), purchase("B", 5)], "XYZ", NOW)
        self.assertTrue(result["insider_cluster_buy_30d"])
        self.assertEqual(result["insider_unique_buyers_30d"], 2)

    def test_role_and_large_purchase_features(self):
        result = build_insider_purchase_features([
            purchase("A", 2, value=250_000, is_officer=True, is_director=True)
        ], "XYZ", NOW)
        self.assertEqual(result["insider_officer_buy_count_30d"], 1)
        self.assertEqual(result["insider_director_buy_count_30d"], 1)
        self.assertTrue(result["insider_large_purchase_30d"])
        self.assertAlmostEqual(result["insider_max_ownership_increase_ratio_30d"], 0.1)

    def test_windows_and_recency(self):
        rows = [purchase("A", 3, 10_000), purchase("B", 20, 20_000), purchase("C", 60, 30_000)]
        result = build_insider_purchase_features(rows, "XYZ", NOW)
        self.assertEqual(result["insider_purchase_count_7d"], 1)
        self.assertEqual(result["insider_purchase_count_30d"], 2)
        self.assertEqual(result["insider_purchase_count_90d"], 3)
        self.assertEqual(result["insider_total_value_90d"], 60_000)
        self.assertEqual(result["insider_days_since_latest_purchase"], 3)


if __name__ == "__main__":
    unittest.main()
