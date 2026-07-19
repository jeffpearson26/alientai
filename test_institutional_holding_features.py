from __future__ import annotations

import unittest

from alientai_v2.features.institutional_holding_features import institutional_holding_features


class InstitutionalHoldingFeatureTests(unittest.TestCase):
    def setUp(self):
        self.document = {
            "collected_at_utc": "2026-07-19T20:00:00Z",
            "payload": {
                "total_institutional_ownership_percentage": "72.5%",
                "total_institutional_holders": "100",
                "total_institutional_shares": "1000",
                "holders_with_increased_holdings": "60", "holders_with_decreased_holdings": "30",
                "shares_with_increased_holdings": "300", "shares_with_decreased_holdings": "100",
                "holdings": [
                    {"shares_held": "200", "last_reported": "2026-06-30"},
                    {"shares_held": "100", "last_reported": "2026-06-30"},
                ],
            },
        }

    def test_future_snapshot_is_hidden(self):
        self.assertFalse(institutional_holding_features(self.document, "2026-07-18T20:00:00Z")["institutional_holdings_available"])

    def test_accumulation_and_concentration(self):
        result = institutional_holding_features(self.document, "2026-07-20T20:00:00Z")
        self.assertEqual(result["institutional_holder_net_increase_count"], 30)
        self.assertEqual(result["institutional_share_net_change"], 200)
        self.assertEqual(result["institutional_accumulation_ratio"], 0.75)
        self.assertEqual(result["institutional_top10_concentration_pct"], 30.0)
        self.assertEqual(result["institutional_ownership_pct"], 72.5)


if __name__ == "__main__":
    unittest.main()
