from __future__ import annotations

import gzip
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from download_alpha_vantage_event_transcripts import fiscal_quarter, run, transcript_requests


class EventTranscriptDownloaderTests(unittest.TestCase):
    def test_fiscal_quarter(self):
        self.assertEqual(fiscal_quarter("2024-09-30"), "2024Q3")

    def test_selects_latest_buffered_earnings_call(self):
        research = [{"symbol": "IBM", "study_role": "winner", "as_of_utc": "2024-05-01T20:00:00Z"}]
        earnings = [
            {"ticker": "IBM", "available_at_utc": "2024-04-30T21:00:00Z", "fiscal_date_ending": "2024-03-31"},
            {"ticker": "IBM", "available_at_utc": "2024-01-20T21:00:00Z", "fiscal_date_ending": "2023-12-31"},
        ]
        self.assertEqual(transcript_requests(research, earnings), [("IBM", "2023Q4")])

    def test_archive_is_compressed_and_resumable(self):
        payload = {"symbol": "IBM", "quarter": "2024Q1", "transcript": [{"speaker": "CEO"}]}
        with TemporaryDirectory() as directory:
            output = Path(directory)
            with patch("download_alpha_vantage_event_transcripts.fetch_transcript", return_value=payload) as fetch:
                first = run([("IBM", "2024Q1")], "secret", output, delay=0)
                second = run([("IBM", "2024Q1")], "secret", output, delay=0)
            with gzip.open(next(output.rglob("*.json.gz")), "rt", encoding="utf-8") as handle:
                archived = json.load(handle)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(first["status"], "complete")
        self.assertEqual(second["status"], "complete")
        self.assertIn("alientai_collected_at_utc", archived)


if __name__ == "__main__":
    unittest.main()
