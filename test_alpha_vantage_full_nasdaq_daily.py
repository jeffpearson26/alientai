from __future__ import annotations

import csv
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from audit_alpha_vantage_full_nasdaq_daily import ten_year_boundary
from download_alpha_vantage_full_nasdaq_daily import (
    canonical_universe_bytes,
    load_listing_rows,
    series_filename,
    sha256_bytes,
    validate_payload,
)


def valid_payload(symbol: str, dates: list[str]) -> dict:
    return {
        "Meta Data": {"2. Symbol": symbol},
        "Time Series (Daily)": {
            market_date: {
                "1. open": "10",
                "2. high": "12",
                "3. low": "9",
                "4. close": "11",
                "5. adjusted close": "11",
                "6. volume": "1000",
                "7. dividend amount": "0",
                "8. split coefficient": "1",
            }
            for market_date in dates
        },
    }


class FullNasdaqDailyTest(unittest.TestCase):
    def test_listing_filter_is_exact_and_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "listing.csv.gz"
            rows = [
                {
                    "symbol": "ZZZ",
                    "name": "Z",
                    "exchange": "NASDAQ",
                    "assetType": "ETF",
                    "ipoDate": "2020-01-01",
                    "delistingDate": "null",
                    "status": "Active",
                },
                {
                    "symbol": "AAA",
                    "name": "A",
                    "exchange": "NASDAQ",
                    "assetType": "Stock",
                    "ipoDate": "2000-01-01",
                    "delistingDate": "null",
                    "status": "Active",
                },
                {
                    "symbol": "DROP1",
                    "name": "D",
                    "exchange": "NYSE",
                    "assetType": "Stock",
                    "ipoDate": "2000-01-01",
                    "delistingDate": "null",
                    "status": "Active",
                },
                {
                    "symbol": "DROP2",
                    "name": "D",
                    "exchange": "NASDAQ",
                    "assetType": "Stock",
                    "ipoDate": "2000-01-01",
                    "delistingDate": "2020-01-01",
                    "status": "Delisted",
                },
            ]
            with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0])
                writer.writeheader()
                writer.writerows(rows)
            actual = load_listing_rows(path)
            self.assertEqual(["AAA", "ZZZ"], [row["symbol"] for row in actual])
            self.assertEqual(["Stock", "ETF"], [row["asset_type"] for row in actual])
            self.assertEqual(
                sha256_bytes(canonical_universe_bytes(actual)),
                sha256_bytes(canonical_universe_bytes(load_listing_rows(path))),
            )

    def test_payload_validation_records_stale_without_rejecting_history(self) -> None:
        details = validate_payload(
            valid_payload("AAA", ["2010-01-04", "2026-08-04"]),
            "AAA",
            expected_latest_date="2026-08-06",
        )
        self.assertEqual("stale", details["freshness"])
        self.assertEqual(2, details["rows"])
        self.assertEqual("2010-01-04", details["first_date"])

    def test_payload_rejects_future_and_wrong_symbol(self) -> None:
        with self.assertRaisesRegex(ValueError, "after expected"):
            validate_payload(
                valid_payload("AAA", ["2026-08-07"]),
                "AAA",
                expected_latest_date="2026-08-06",
            )
        with self.assertRaisesRegex(ValueError, "payload symbol"):
            validate_payload(
                valid_payload("BBB", ["2026-08-06"]),
                "AAA",
                expected_latest_date="2026-08-06",
            )

    def test_filename_is_windows_safe_and_symbol_specific(self) -> None:
        first = series_filename("-P/HIZ")
        second = series_filename("-P.HIZ")
        self.assertRegex(first, r"^[0-9a-f]{64}\.json\.gz$")
        self.assertNotEqual(first, second)

    def test_ten_year_boundary(self) -> None:
        from datetime import date

        self.assertEqual(date(2016, 8, 6), ten_year_boundary(date(2026, 8, 6)))
        self.assertEqual(date(2016, 2, 28), ten_year_boundary(date(2026, 2, 28)))


if __name__ == "__main__":
    unittest.main()
