from __future__ import annotations

import gzip
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from download_alpha_vantage_event_news import event_requests, run, safe_error


class EventNewsDownloaderTests(unittest.TestCase):
    def test_event_requests_use_as_of_and_role(self):
        rows = [
            {"symbol": "ibm", "study_role": "winner", "as_of_utc": "2024-01-05T20:00:00Z"},
            {"symbol": "MSFT", "study_role": "control", "as_of_utc": "2024-01-05T20:00:00Z"},
        ]
        items = event_requests(rows)
        self.assertEqual(items[0][0], "IBM")
        self.assertEqual(items[0][1], datetime(2024, 1, 5, 20, tzinfo=timezone.utc))
        self.assertEqual(len(items), 1)

    def test_archive_is_resumable_and_records_cutoff(self):
        as_of = datetime(2024, 1, 5, 20, tzinfo=timezone.utc)
        with TemporaryDirectory() as directory:
            output = Path(directory)
            with patch("download_alpha_vantage_event_news.fetch_news", return_value={"feed": []}) as fetch:
                first = run([("IBM", as_of)], "secret", output, delay=0)
                second = run([("IBM", as_of)], "secret", output, delay=0)
            archive = next(output.rglob("*.json.gz"))
            with gzip.open(archive, "rt", encoding="utf-8") as handle:
                payload = json.load(handle)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(first["status"], "complete")
        self.assertEqual(second["status"], "complete")
        self.assertEqual(payload["alientai_request"]["as_of_utc"], as_of.isoformat())

    def test_error_redacts_key(self):
        self.assertNotIn("SECRET", safe_error("bad SECRET", "SECRET"))


if __name__ == "__main__":
    unittest.main()
