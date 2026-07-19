from __future__ import annotations

import gzip
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from download_alpha_vantage_historical_options import archive_path, event_requests, run, safe_error


class HistoricalOptionsDownloaderTests(unittest.TestCase):
    def test_builds_deduplicated_entry_and_exit_requests(self):
        rows = [{"symbol": "ibm", "study_role": "winner", "market_date": "2024-01-02", "future_market_date": "2024-01-09"}] * 2
        self.assertEqual(event_requests(rows), [("IBM", "2024-01-02"), ("IBM", "2024-01-09")])

    def test_role_filter_excludes_controls(self):
        rows = [{"symbol": "IBM", "study_role": "control", "market_date": "2024-01-02", "future_market_date": "2024-01-09"}]
        self.assertEqual(event_requests(rows), [])

    def test_writes_compressed_chain_and_resumes(self):
        payload = {"data": [{"contractID": "IBM240119C00150000"}]}
        with TemporaryDirectory() as directory:
            output = Path(directory)
            with patch("download_alpha_vantage_historical_options.fetch_chain", return_value=payload) as fetch:
                first = run([("IBM", "2024-01-05")], "secret", output, delay=0)
                second = run([("IBM", "2024-01-05")], "secret", output, delay=0)
            path = archive_path(output, "IBM", "2024-01-05")
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                self.assertEqual(json.load(handle), payload)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(first["status"], "complete")
        self.assertEqual(second["status"], "complete")

    def test_error_redacts_key(self):
        self.assertNotIn("SECRET", safe_error("bad SECRET", "SECRET"))


if __name__ == "__main__":
    unittest.main()
