from __future__ import annotations

import unittest

from alientai_v2.features.short_interest_features import build_short_interest_features


def snapshot(available, shares=1_000_000, **extra):
    row = {
        "ticker": "XYZ", "settlement_date": "2026-01-15",
        "publication_timestamp_utc": available, "available_at_utc": available,
        "short_interest_shares": shares, "float_shares": 5_000_000,
        "shares_outstanding": 10_000_000, "average_daily_volume": 250_000,
        "is_training_eligible": True,
    }
    row.update(extra)
    return row


class ShortInterestFeatureTests(unittest.TestCase):
    def test_settlement_date_does_not_make_unpublished_snapshot_visible(self):
        row = snapshot("2026-01-27T23:59:59Z")
        result = build_short_interest_features([row], "XYZ", "2026-01-20T21:00:00Z")
        self.assertFalse(result["short_interest_available"])

    def test_latest_published_snapshot_builds_squeeze_features(self):
        row = snapshot("2026-01-27T12:00:00Z")
        result = build_short_interest_features([row], "XYZ", "2026-01-28T12:00:00Z")
        self.assertEqual(result["short_interest_pct_float"], 20.0)
        self.assertEqual(result["short_interest_pct_outstanding"], 10.0)
        self.assertEqual(result["short_interest_days_to_cover"], 4.0)
        self.assertTrue(result["short_interest_high_squeeze_pressure"])
        self.assertEqual(result["short_interest_report_age_days"], 1.0)

    def test_change_uses_prior_published_snapshot(self):
        earlier = snapshot("2026-01-10T12:00:00Z", shares=800_000)
        latest = snapshot("2026-01-27T12:00:00Z", shares=1_000_000)
        result = build_short_interest_features([latest, earlier], "XYZ", "2026-01-28T12:00:00Z")
        self.assertEqual(result["short_interest_change_from_prior_pct"], 25.0)

    def test_quarantined_snapshot_is_invisible(self):
        row = snapshot("2026-01-27T12:00:00Z", is_training_eligible=False)
        self.assertFalse(build_short_interest_features([row], "XYZ", "2026-01-28T12:00:00Z")["short_interest_available"])

    def test_explicit_days_to_cover_is_preserved(self):
        row = snapshot("2026-01-27T12:00:00Z", days_to_cover=7.5)
        result = build_short_interest_features([row], "XYZ", "2026-01-28T12:00:00Z")
        self.assertEqual(result["short_interest_days_to_cover"], 7.5)


if __name__ == "__main__":
    unittest.main()
