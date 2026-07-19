from __future__ import annotations

import unittest

from alientai_v2.features.shares_outstanding_features import shares_outstanding_features


class SharesOutstandingFeatureTests(unittest.TestCase):
    def setUp(self):
        rows = []
        for date, basic in [
            ("2026-06-30", 90), ("2026-03-31", 95), ("2025-12-31", 96),
            ("2025-09-30", 98), ("2025-06-30", 100),
        ]:
            rows.append({"date": date, "shares_outstanding_basic": str(basic), "shares_outstanding_diluted": str(basic + 2)})
        self.document = {"collected_at_utc": "2026-07-19T20:00:00Z", "payload": {"data": rows}}

    def test_future_snapshot_is_hidden(self):
        self.assertFalse(shares_outstanding_features(self.document, "2026-07-18T20:00:00Z")["shares_outstanding_available"])

    def test_computes_buyback_and_dilution_features(self):
        result = shares_outstanding_features(self.document, "2026-07-20T20:00:00Z")
        self.assertTrue(result["shares_outstanding_available"])
        self.assertAlmostEqual(result["shares_basic_qoq_change_pct"], -5.2631579)
        self.assertAlmostEqual(result["shares_basic_yoy_change_pct"], -10.0)
        self.assertAlmostEqual(result["shares_dilution_pct"], 2.2222222)


if __name__ == "__main__":
    unittest.main()
