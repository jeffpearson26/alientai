from __future__ import annotations

import unittest

from upload_earnings_to_supabase import sanitize_row, upload


class FakeQuery:
    def __init__(self):
        self.calls = []

    def upsert(self, rows, on_conflict=None):
        self.calls.append((rows, on_conflict))
        return self

    def execute(self):
        return self


class FakeClient:
    def __init__(self):
        self.query = FakeQuery()
        self.tables = []

    def table(self, name):
        self.tables.append(name)
        return self.query


def valid_row():
    return {
        "event_id": "a", "ticker": "IBM", "fiscal_date_ending": "2026-03-31",
        "reported_date": "2026-04-22", "available_at_utc": "2026-04-22T20:30:00Z",
        "reported_eps": 1.5, "estimated_eps": 1.25, "surprise": 0.25,
        "surprise_percentage": 20.0, "source": "ALPHA_VANTAGE_EARNINGS",
        "source_url": "https://www.alphavantage.co/query?function=EARNINGS",
        "quality_flags": [], "is_training_eligible": True,
    }


class EarningsUploaderTests(unittest.TestCase):
    def test_valid_row_remains_eligible(self):
        self.assertTrue(sanitize_row(valid_row())["is_training_eligible"])

    def test_future_fiscal_date_is_quarantined(self):
        row = valid_row()
        row["fiscal_date_ending"] = "2026-05-01"
        cleaned = sanitize_row(row)
        self.assertFalse(cleaned["is_training_eligible"])
        self.assertIn("FISCAL_DATE_AFTER_REPORTED_DATE", cleaned["quality_flags"])

    def test_dry_run_has_no_client_calls(self):
        result = upload(None, [valid_row()], 100, dry_run=True)
        self.assertEqual(result["status"], "dry_run")

    def test_upload_uses_event_id_upsert(self):
        client = FakeClient()
        result = upload(client, [valid_row()], 100)
        self.assertEqual(result["uploaded_rows"], 1)
        self.assertEqual(client.tables, ["v2_earnings_events"])
        self.assertEqual(client.query.calls[0][1], "event_id")


if __name__ == "__main__":
    unittest.main()
