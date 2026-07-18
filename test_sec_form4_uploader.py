from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from upload_sec_form4_to_supabase import batches, sanitize_row, upload


def row(identifier="a"):
    return {
        "transaction_id": identifier, "ticker": "XYZ", "cik": "123",
        "accession_number": "0001", "filing_timestamp_utc": "2026-01-01T20:00:00Z",
        "available_at_utc": "2026-01-01T20:00:00Z", "transaction_date": "2025-12-31",
        "transaction_code": "P", "shares": 10, "price": 5, "total_value": 50,
        "source_url": "https://www.sec.gov/example", "source": "SEC_QUARTERLY_345",
    }


class FakeQuery:
    def __init__(self, client): self.client = client
    def upsert(self, values, on_conflict):
        self.client.calls.append((values, on_conflict))
        return self
    def execute(self): return {"data": []}


class FakeClient:
    def __init__(self): self.calls = []; self.tables = []
    def table(self, name): self.tables.append(name); return FakeQuery(self)


class SECUploaderTests(unittest.TestCase):
    def test_generated_total_value_is_not_uploaded(self):
        cleaned = sanitize_row(row())
        self.assertNotIn("total_value", cleaned)

    def test_non_purchase_fails_closed(self):
        bad = row(); bad["transaction_code"] = "A"
        with self.assertRaises(ValueError): sanitize_row(bad)

    def test_batches_are_bounded(self):
        self.assertEqual([len(x) for x in batches([row(str(i)) for i in range(5)], 2)], [2, 2, 1])

    def test_upload_uses_transaction_id_upsert(self):
        client = FakeClient()
        with tempfile.TemporaryDirectory() as directory:
            result = upload(
                client=client, table="target", rows=[row("a"), row("b")], batch_size=1,
                state_path=Path(directory) / "state.json",
            )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["uploaded_rows"], 2)
        self.assertTrue(all(call[1] == "transaction_id" for call in client.calls))

    def test_dry_run_makes_no_client_calls(self):
        client = FakeClient()
        result = upload(client=client, table="target", rows=[row()], batch_size=10, dry_run=True)
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
