from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from download_sec_form4_quarterly import merge_records, quarter_range, quarter_url


class SECDownloaderTests(unittest.TestCase):
    def test_quarter_url_matches_sec_convention(self):
        self.assertEqual(
            quarter_url(2026, 2),
            "https://www.sec.gov/files/datastandardsinnovation/data/insider-transactions-data-sets/2026q2_form345.zip",
        )

    def test_quarter_range_crosses_year(self):
        self.assertEqual(quarter_range(2025, 4, 2026, 2), [(2025, 4), (2026, 1), (2026, 2)])

    def test_merge_is_resumable_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.jsonl"
            first = {"transaction_id": "a", "available_at_utc": "2026-01-01", "ticker": "A"}
            changed = {"transaction_id": "a", "available_at_utc": "2026-01-01", "ticker": "A", "x": 1}
            second = {"transaction_id": "b", "available_at_utc": "2026-01-02", "ticker": "B"}
            self.assertEqual(merge_records(path, [first]), 1)
            self.assertEqual(merge_records(path, [changed, second]), 2)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows[0]["x"], 1)


if __name__ == "__main__":
    unittest.main()
