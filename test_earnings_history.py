from __future__ import annotations

import unittest
from datetime import datetime

from alientai_v2.data.earnings_history import (
    conservative_available_at, merge_events, normalize_response,
)
from download_alpha_vantage_earnings import safe_error


class EarningsHistoryTests(unittest.TestCase):
    def test_premarket_is_visible_before_same_day_close(self):
        available = datetime.fromisoformat(conservative_available_at("2026-07-17", "pre-market").replace("Z", "+00:00"))
        self.assertEqual(available.date().isoformat(), "2026-07-17")

    def test_postmarket_is_after_same_day_close(self):
        available = datetime.fromisoformat(conservative_available_at("2026-07-17", "post-market").replace("Z", "+00:00"))
        self.assertGreaterEqual(available.hour, 20)

    def test_unknown_timing_fails_conservatively_to_next_day(self):
        available = datetime.fromisoformat(conservative_available_at("2026-07-17", "").replace("Z", "+00:00"))
        self.assertEqual(available.date().isoformat(), "2026-07-18")

    def test_normalizes_surprise_without_future_fields(self):
        rows = normalize_response("ibm", {"quarterlyEarnings": [{
            "fiscalDateEnding": "2026-03-31", "reportedDate": "2026-04-22",
            "reportedEPS": "1.50", "estimatedEPS": "1.25", "surprise": "0.25",
            "surprisePercentage": "20", "reportTime": "post-market",
        }]})
        self.assertEqual(rows[0]["ticker"], "IBM")
        self.assertEqual(rows[0]["surprise_percentage"], 20.0)
        self.assertTrue(rows[0]["is_training_eligible"])

    def test_rate_limit_message_fails_closed(self):
        with self.assertRaises(RuntimeError):
            normalize_response("IBM", {"Note": "limit reached"})

    def test_merge_is_idempotent(self):
        row = {"event_id": "a", "available_at_utc": "2026-01-01", "x": 1}
        changed = {**row, "x": 2}
        self.assertEqual(merge_events([row], [changed]), [changed])

    def test_provider_error_never_exposes_api_key(self):
        secret = "TOPSECRET123"
        cleaned = safe_error(f"API key {secret} exceeded 25 requests per day rate limit", secret)
        self.assertNotIn(secret, cleaned)
        self.assertIn("rate limit", cleaned.lower())


if __name__ == "__main__":
    unittest.main()
