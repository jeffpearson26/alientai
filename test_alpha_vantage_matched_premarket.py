from __future__ import annotations

import gzip
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from download_alpha_vantage_matched_premarket import (
    archive_path, ensure_free_space, event_requests, fetch_current, run,
    run_current, unavailable_response, validate_current_request,
)


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
        self.assertEqual(first["mode"], "historical")
        self.assertEqual(first["entitlement"], "historical")

    def test_all_role_accepts_natural_universe_rows_without_study_role(self):
        rows = [{"symbol": "IBM", "market_date": "2024-01-02", "future_market_date": "2024-01-09"}]
        self.assertEqual(event_requests(rows, "all"), [("IBM", "2024-01")])

    def test_low_disk_space_fails_closed(self):
        usage = type("Usage", (), {"free": 1 * 1024 ** 3})()
        with TemporaryDirectory() as directory:
            with patch("download_alpha_vantage_matched_premarket.shutil.disk_usage", return_value=usage):
                with self.assertRaisesRegex(RuntimeError, "low disk space"):
                    ensure_free_space(Path(directory), 6.0)

    def test_invalid_symbol_response_is_unavailable_and_resumable(self):
        message = "Invalid API call. Please retry or visit the documentation for TIME_SERIES_INTRADAY."
        with TemporaryDirectory() as directory:
            output = Path(directory)
            with patch("download_alpha_vantage_matched_premarket.fetch_month", side_effect=RuntimeError(message)) as fetch:
                first = run([("BRK.B", "2022-10")], "secret", output, delay=0)
                second = run([("BRK.B", "2022-10")], "secret", output, delay=0)
        self.assertTrue(unavailable_response(message))
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(first["unavailable"], ["BRK.B|2022-10"])
        self.assertEqual(second["status"], "complete")

    def test_rate_limit_is_not_unavailable(self):
        self.assertFalse(unavailable_response("Minute-level rate limit exceed."))

    def test_actionable_runtime_failure_is_persisted_fail_closed(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            with patch(
                "download_alpha_vantage_matched_premarket.fetch_current",
                side_effect=RuntimeError("not entitled to realtime data"),
            ):
                with self.assertRaisesRegex(RuntimeError, "not entitled"):
                    run_current(
                        ["IBM"],
                        "2026-08-03",
                        "secret",
                        output,
                        "realtime",
                        delay=0,
                    )
            manifest = json.loads(
                (output / "manifest.json").read_text(encoding="utf-8")
            )
        self.assertEqual(manifest["status"], "failed_closed")
        self.assertEqual(len(manifest["failed"]), 1)
        self.assertNotIn("secret", json.dumps(manifest))

    def test_current_request_requires_exact_date_and_completed_cutoff(self):
        rows = [
            {
                "symbol": "IBM",
                "market_date": "2026-08-03",
                "as_of_utc": "2026-08-03T13:25:00+00:00",
            }
        ]
        validate_current_request(
            rows,
            "2026-08-03",
            datetime(2026, 8, 3, 13, 26, tzinfo=timezone.utc),
        )
        with self.assertRaisesRegex(ValueError, "earlier than"):
            validate_current_request(
                rows,
                "2026-08-03",
                datetime(2026, 8, 3, 13, 24, tzinfo=timezone.utc),
            )

    def test_current_fetch_uses_entitlement_and_omits_month(self):
        response = type(
            "Response",
            (),
            {"content": CSV, "json": lambda self: {}},
        )()
        with patch(
            "download_alpha_vantage_matched_premarket.get_alpha_vantage_response",
            return_value=response,
        ) as request:
            content = fetch_current("IBM", "secret", "realtime")
        params = request.call_args.args[0]
        self.assertEqual(content, CSV)
        self.assertEqual(params["entitlement"], "realtime")
        self.assertNotIn("month", params)

    def test_current_archive_freezes_date_and_entitlement(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            with patch(
                "download_alpha_vantage_matched_premarket.fetch_current",
                return_value=CSV,
            ) as fetch:
                first = run_current(
                    ["IBM"],
                    "2026-08-03",
                    "secret",
                    output,
                    "realtime",
                    delay=0,
                )
                second = run_current(
                    ["IBM"],
                    "2026-08-03",
                    "secret",
                    output,
                    "realtime",
                    delay=0,
                )
            with self.assertRaisesRegex(ValueError, "manifest contract mismatch"):
                run_current(
                    ["IBM"],
                    "2026-08-03",
                    "secret",
                    output,
                    "delayed",
                    delay=0,
                )
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(first["status"], "complete")
        self.assertEqual(second["status"], "complete")
        self.assertEqual(first["timestamp_convention"], "interval_start")
        self.assertEqual(first["bar_interval_minutes"], 5)


if __name__ == "__main__":
    unittest.main()
