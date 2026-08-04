from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import download_alpha_vantage_adjusted_intraday_archive as archive


CSV = b"""timestamp,open,high,low,close,volume
2026-07-01 09:35:00,10.0,10.5,9.9,10.2,100
2026-07-01 09:30:00,9.8,10.1,9.7,10.0,200
"""


class AdjustedIntradayArchiveTests(unittest.TestCase):
    def test_month_range_is_inclusive(self):
        self.assertEqual(
            archive.month_range("2025-11", "2026-02"),
            ["2025-11", "2025-12", "2026-01", "2026-02"],
        )

    def test_symbols_include_benchmarks_and_deduplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "symbols.txt"
            path.write_text("AMD\nNVDA\nAMD\n", encoding="utf-8")
            self.assertEqual(
                archive.read_symbols(path, ["QQQ", "SPY", "NVDA"]),
                ["AMD", "NVDA", "QQQ", "SPY"],
            )

    def test_validates_month_and_candle_integrity(self):
        result = archive.validate_csv_content(CSV, "2026-07")
        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["first_timestamp_et"], "2026-07-01 09:30:00")
        self.assertEqual(result["last_timestamp_et"], "2026-07-01 09:35:00")

    def test_rejects_mismatched_month(self):
        with self.assertRaisesRegex(ValueError, "mismatched month"):
            archive.validate_csv_content(CSV, "2026-06")

    def test_fetch_contract_requests_adjusted_extended_five_minute_csv(self):
        class Response:
            content = CSV

        with patch.object(
            archive, "get_alpha_vantage_response", return_value=Response()
        ) as request:
            content, metadata = archive.fetch_month("AMD", "2026-07", "secret")
        self.assertEqual(content, CSV)
        self.assertEqual(metadata["rows"], 2)
        params = request.call_args.args[0]
        self.assertEqual(params["function"], "TIME_SERIES_INTRADAY")
        self.assertEqual(params["interval"], "5min")
        self.assertEqual(params["month"], "2026-07")
        self.assertEqual(params["adjusted"], "true")
        self.assertEqual(params["extended_hours"], "true")
        self.assertEqual(params["datatype"], "csv")

    def test_limited_run_is_resumable_and_adopts_valid_file(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            symbols = ["AMD", "QQQ"]
            destination = archive.archive_path(output, "AMD", "2026-07")
            destination.parent.mkdir(parents=True)
            with gzip.open(destination, "wb") as handle:
                handle.write(CSV)

            result = archive.run(
                symbols=symbols,
                start_month="2026-07",
                end_month="2026-07",
                api_key="secret",
                output=output,
                delay_seconds=0,
                minimum_free_gb=0,
                limit_requests=1,
            )
            self.assertEqual(result["status"], "partial_limit")
            self.assertEqual(len(result["completed"]), 1)
            self.assertEqual(result["completed"][0]["request"], "AMD|2026-07")

            with patch.object(archive, "fetch_month", return_value=(CSV, archive.validate_csv_content(CSV, "2026-07"))):
                resumed = archive.run(
                    symbols=symbols,
                    start_month="2026-07",
                    end_month="2026-07",
                    api_key="secret",
                    output=output,
                    delay_seconds=0,
                    minimum_free_gb=0,
                )
            self.assertEqual(resumed["status"], "complete")
            self.assertEqual(len(resumed["completed"]), 2)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "complete")
            self.assertEqual(manifest["request_count"], 2)

    def test_existing_manifest_contract_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            contract = archive.manifest_contract(["AMD"], "2026-07", "2026-07")
            manifest = archive.new_manifest(contract)
            manifest["adjusted"] = False
            (output / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "adjusted"):
                archive.load_manifest(output / "manifest.json", contract)


if __name__ == "__main__":
    unittest.main()
