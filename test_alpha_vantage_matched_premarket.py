from __future__ import annotations

import gzip
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from download_alpha_vantage_matched_premarket import archive_path, event_requests, run


CSV = b"timestamp,open,high,low,close,volume\n2024-01-02 09:25:00,10,11,9,10.5,1000\n"


class AlphaVantageMatchedPremarketTests(unittest.TestCase):
    def test_requests_deduplicate_symbol_month_and_filter_role(self):
        rows = [
            {"symbol": "ibm", "market_date": "2024-01-02", "future_market_date": "2024-02-02", "study_role": "winner"},
            {"symbol": "IBM", "market_date": "2024-01-20", "study_role": "winner"},
            {"symbol": "MSFT", "market_date": "2024-01-03", "study_role": "control"},
        ]
        self.assertEqual(event_requests(rows, "winner"), [("IBM", "2024-01"), ("IBM", "2024-02")])
        self.assertEqual(len(event_requests(rows, "all")), 3)

    def test_archive_is_compressed_and_resume_safe(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            with patch("download_alpha_vantage_matched_premarket.fetch_month", return_value=CSV) as fetch:
                first = run([("IBM", "2024-01")], "secret", output, delay=0)
                second = run([("IBM", "2024-01")], "secret", output, delay=0)
            path = archive_path(output, "IBM", "2024-01")
            with gzip.open(path, "rb") as handle:
                content = handle.read()
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(content, CSV)
        self.assertEqual(first["status"], "complete")
        self.assertEqual(second["status"], "complete")


if __name__ == "__main__":
    unittest.main()
