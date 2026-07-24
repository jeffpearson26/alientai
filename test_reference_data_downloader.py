from __future__ import annotations

import gzip
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from download_alpha_vantage_reference_data import requests_to_archive, run, safe_message


class ReferenceDataDownloaderTests(unittest.TestCase):
    def test_includes_active_and_delisted_universes(self):
        names = {name for name, _ in requests_to_archive()}
        self.assertIn("listing_status_active", names)
        self.assertIn("listing_status_delisted", names)

    def test_includes_dated_listing_snapshot_with_validated_date(self):
        names_and_params = requests_to_archive(["2020-06-30"])
        params = dict(names_and_params)["listing_status_active_2020-06-30"]
        self.assertEqual(params["date"], "2020-06-30")
        with self.assertRaises(ValueError):
            requests_to_archive(["June 30 2020"])

    def test_archives_compressed_content_with_hash(self):
        with TemporaryDirectory() as directory:
            with patch("download_alpha_vantage_reference_data.fetch", return_value=b"symbol,name\nIBM,IBM\n"):
                result = run(Path(directory), "secret")
            first = Path(result["files"][0]["path"])
            with gzip.open(first, "rb") as handle:
                self.assertEqual(handle.read(), b"symbol,name\nIBM,IBM\n")
        self.assertEqual(len(result["files"]), 4)
        self.assertEqual(len(result["files"][0]["sha256"]), 64)

    def test_error_redacts_key(self):
        self.assertNotIn("SECRET", safe_message("bad SECRET", "SECRET"))


if __name__ == "__main__":
    unittest.main()
