from __future__ import annotations

import gzip
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from download_alpha_vantage_fundamental_snapshots import run, safe_error, unavailable_response


class FundamentalSnapshotDownloaderTests(unittest.TestCase):
    def test_snapshot_is_timestamped_compressed_and_resumable(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            with patch("download_alpha_vantage_fundamental_snapshots.fetch", return_value={"symbol": "IBM", "estimates": []}) as fetch:
                first = run(["IBM"], ["EARNINGS_ESTIMATES"], "secret", output, delay=0)
                second = run(["IBM"], ["EARNINGS_ESTIMATES"], "secret", output, delay=0)
            path = output / "earnings_estimates" / "IBM.json.gz"
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                document = json.load(handle)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(first["status"], "complete")
        self.assertEqual(second["status"], "complete")
        self.assertEqual(document["endpoint"], "EARNINGS_ESTIMATES")
        self.assertIn("collected_at_utc", document)

    def test_rejects_unapproved_endpoint(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                run(["IBM"], ["NOT_REAL"], "secret", Path(directory), delay=0)

    def test_error_redacts_key(self):
        self.assertNotIn("SECRET", safe_error("bad SECRET", "SECRET"))

    def test_invalid_symbol_response_is_unavailable_and_resume_safe(self):
        message = "Invalid API call. Please retry or visit the documentation for INCOME_STATEMENT."
        with TemporaryDirectory() as directory:
            output = Path(directory)
            with patch("download_alpha_vantage_fundamental_snapshots.fetch", side_effect=RuntimeError(message)) as fetch:
                first = run(["BCOR"], ["INCOME_STATEMENT"], "secret", output, delay=0)
                second = run(["BCOR"], ["INCOME_STATEMENT"], "secret", output, delay=0)
        self.assertTrue(unavailable_response(message))
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(first["status"], "complete")
        self.assertEqual(second["status"], "complete")
        self.assertEqual(first["unavailable"], ["INCOME_STATEMENT|BCOR"])

    def test_rate_limit_is_not_misclassified_as_unavailable(self):
        self.assertFalse(unavailable_response("Minute-level rate limit exceed."))


if __name__ == "__main__":
    unittest.main()
