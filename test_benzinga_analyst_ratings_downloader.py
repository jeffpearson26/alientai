from __future__ import annotations

import gzip
import json
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from download_benzinga_analyst_ratings import archive_path, date_windows, run, safe_error


ROW = {
    "id": "abc", "date": "2026-01-05", "time": "14:52:07", "ticker": "MNDY",
    "action_company": "Upgrades", "rating_prior": "Hold", "rating_current": "Buy",
    "pt_prior": "200", "pt_current": "260", "analyst": "Example Firm", "currency": "USD",
}


class BenzingaAnalystRatingDownloaderTests(unittest.TestCase):
    def test_date_windows_are_complete_and_non_overlapping(self):
        windows = date_windows(date(2026, 1, 1), date(2026, 3, 2), 30)
        self.assertEqual(windows[0], (date(2026, 1, 1), date(2026, 1, 30)))
        self.assertEqual(windows[-1][1], date(2026, 3, 2))
        self.assertEqual(windows[1][0], windows[0][1].fromordinal(windows[0][1].toordinal() + 1))

    def test_archive_is_normalized_compressed_and_resumable(self):
        window = (date(2026, 1, 1), date(2026, 1, 30))
        with TemporaryDirectory() as directory:
            output = Path(directory)
            with patch("download_benzinga_analyst_ratings.fetch_window", return_value=[ROW]) as fetch:
                first = run([window], "secret", output)
                second = run([window], "secret", output)
            with gzip.open(archive_path(output, *window), "rt", encoding="utf-8") as handle:
                document = json.loads(handle.readline())
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(first["status"], "complete")
        self.assertEqual(second["status"], "complete")
        self.assertEqual(document["normalized"]["normalized_action"], "upgrade")
        self.assertEqual(document["normalized"]["normalized_score_change"], 1.0)

    def test_token_is_redacted(self):
        self.assertNotIn("SECRET", safe_error("bad SECRET", "SECRET"))


if __name__ == "__main__":
    unittest.main()
