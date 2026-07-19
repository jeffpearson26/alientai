from __future__ import annotations

import gzip
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from download_alpha_vantage_fundamental_snapshots import run, safe_error


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


if __name__ == "__main__":
    unittest.main()
