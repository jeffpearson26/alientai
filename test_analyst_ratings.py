from __future__ import annotations

import unittest

from alientai_v2.data.analyst_ratings import normalize_benzinga, normalize_event


class AnalystRatingsTests(unittest.TestCase):
    def test_raw_firm_wording_is_preserved_and_unknown(self):
        row = normalize_event(
            provider="BENZINGA", ticker="XYZ", announcement_timestamp="2026-07-18T12:00:00Z",
            analyst_firm="Example Firm", action="Upgrades", old_rating="Market Perform",
            new_rating="Outperform", source_id="1",
        )
        self.assertEqual(row["old_rating"], "Market Perform")
        self.assertEqual(row["new_rating"], "Outperform")
        self.assertIsNone(row["old_rating_score"])
        self.assertIsNone(row["new_rating_score"])
        self.assertIsNone(row["normalized_score_change"])

    def test_unambiguous_hold_to_buy_is_scored(self):
        row = normalize_event(
            provider="BENZINGA", ticker="XYZ", announcement_timestamp="2026-07-18T12:00:00Z",
            action="Upgrades", old_rating="Hold", new_rating="Buy", source_id="2",
        )
        self.assertEqual(row["normalized_action"], "upgrade")
        self.assertEqual(row["normalized_score_change"], 1.0)

    def test_benzinga_stream_shape_is_supported(self):
        row = normalize_benzinga({
            "data": {"id": "abc", "timestamp": "2026-07-18T12:00:00Z", "content": {
                "ticker": "AAPL", "action_company": "Maintains", "rating_prior": "Buy",
                "rating_current": "Buy", "pt_prior": "180", "pt_current": "200",
                "analyst": "Goldman Sachs",
            }}
        })
        self.assertEqual(row["ticker"], "AAPL")
        self.assertEqual(row["analyst_firm"], "Goldman Sachs")
        self.assertEqual(row["old_price_target"], 180.0)
        self.assertEqual(row["new_price_target"], 200.0)
        self.assertEqual(row["normalized_action"], "maintain")

    def test_missing_timestamp_fails_closed(self):
        with self.assertRaises(ValueError):
            normalize_event(provider="FMP", ticker="XYZ", announcement_timestamp="")


if __name__ == "__main__":
    unittest.main()
