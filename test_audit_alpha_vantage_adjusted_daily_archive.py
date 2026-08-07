from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from audit_alpha_vantage_adjusted_daily_archive import audit_archive


def row(close: str = "10.5") -> dict[str, str]:
    return {
        "1. open": "10",
        "2. high": "11",
        "3. low": "9",
        "4. close": close,
        "5. adjusted close": close,
        "6. volume": "1000",
        "7. dividend amount": "0",
        "8. split coefficient": "1",
    }


class AlphaVantageAdjustedDailyArchiveAuditTests(unittest.TestCase):
    def test_complete_exact_archive_passes(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            symbols = ["AAA", "SPY"]
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "status": "complete",
                        "completed": symbols,
                        "failed": {},
                        "function": "TIME_SERIES_DAILY_ADJUSTED",
                        "outputsize": "full",
                    }
                ),
                encoding="utf-8",
            )
            for symbol in symbols:
                (root / f"{symbol}_daily.json").write_text(
                    json.dumps(
                        {
                            "Meta Data": {"2. Symbol": symbol},
                            "Time Series (Daily)": {
                                "2026-08-05": row("10.2"),
                                "2026-08-06": row("10.5"),
                            },
                        }
                    ),
                    encoding="utf-8",
                )
            result = audit_archive(
                root, symbols, required_latest_date="2026-08-06"
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["common_date_count"], 2)

    def test_stale_or_malformed_payload_fails(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            symbols = ["AAA"]
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "status": "complete",
                        "completed": symbols,
                        "failed": {},
                        "function": "TIME_SERIES_DAILY_ADJUSTED",
                        "outputsize": "full",
                    }
                ),
                encoding="utf-8",
            )
            bad = row()
            bad["2. high"] = "8"
            (root / "AAA_daily.json").write_text(
                json.dumps(
                    {"Time Series (Daily)": {"2026-08-05": bad}}
                ),
                encoding="utf-8",
            )
            result = audit_archive(
                root, symbols, required_latest_date="2026-08-06"
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("AAA", result["failures"])

    def test_payload_symbol_mismatch_fails(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            symbols = ["AAA"]
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "status": "complete",
                        "completed": symbols,
                        "failed": {},
                        "function": "TIME_SERIES_DAILY_ADJUSTED",
                        "outputsize": "full",
                    }
                ),
                encoding="utf-8",
            )
            (root / "AAA_daily.json").write_text(
                json.dumps(
                    {
                        "Meta Data": {"2. Symbol": "BBB"},
                        "Time Series (Daily)": {"2026-08-06": row()},
                    }
                ),
                encoding="utf-8",
            )
            result = audit_archive(
                root, symbols, required_latest_date="2026-08-06"
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("payload symbol", result["failures"]["AAA"])


if __name__ == "__main__":
    unittest.main()
