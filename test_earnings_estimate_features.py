from __future__ import annotations

import unittest

from alientai_v2.features.earnings_estimate_features import earnings_estimate_features


class EarningsEstimateFeatureTests(unittest.TestCase):
    def setUp(self):
        self.document = {
            "collected_at_utc": "2026-07-19T20:00:00Z",
            "payload": {"estimates": [{
                "date": "2026-09-30", "horizon": "fiscal quarter",
                "eps_estimate_average": "2.00", "eps_estimate_average_7_days_ago": "1.90",
                "eps_estimate_average_30_days_ago": "1.80", "eps_estimate_average_60_days_ago": "1.70",
                "eps_estimate_average_90_days_ago": "1.60", "eps_estimate_high": "2.20",
                "eps_estimate_low": "1.70", "eps_estimate_revision_up_trailing_7_days": "3",
                "eps_estimate_revision_down_trailing_7_days": "1",
                "eps_estimate_revision_up_trailing_30_days": "8",
                "eps_estimate_revision_down_trailing_30_days": "2",
                "eps_estimate_analyst_count": "20", "revenue_estimate_analyst_count": "18",
            }]},
        }

    def test_future_snapshot_is_not_visible(self):
        result = earnings_estimate_features(self.document, "2026-07-18T20:00:00Z")
        self.assertFalse(result["earnings_estimate_available"])

    def test_revision_features_use_only_snapshot_fields(self):
        result = earnings_estimate_features(self.document, "2026-07-20T20:00:00Z")
        self.assertTrue(result["earnings_estimate_available"])
        self.assertAlmostEqual(result["earnings_estimate_eps_change_30d_pct"], 11.111111, places=5)
        self.assertEqual(result["earnings_estimate_revision_net_7d"], 2)
        self.assertEqual(result["earnings_estimate_revision_net_30d"], 6)
        self.assertEqual(result["earnings_estimate_analyst_count"], 20)

    def test_selects_nearest_future_quarter(self):
        later = dict(self.document["payload"]["estimates"][0], date="2026-12-31", eps_estimate_average="9")
        self.document["payload"]["estimates"].insert(0, later)
        result = earnings_estimate_features(self.document, "2026-07-20T20:00:00Z")
        self.assertEqual(result["earnings_estimate_eps_average"], 2.0)


if __name__ == "__main__":
    unittest.main()
