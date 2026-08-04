from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from download_alpha_vantage_historical_options import fetch_chain
from download_alpha_vantage_option_panel import market_weekdays, panel_requests, read_symbols


class OptionPanelDownloaderTests(unittest.TestCase):
    @patch("download_alpha_vantage_historical_options.get_alpha_vantage_response")
    def test_empty_provider_chain_is_unavailable_not_completed(self, get_response):
        response = Mock()
        response.json.return_value = {
            "endpoint": "Historical Options",
            "message": "No data for this symbol and trading day.",
            "data": [],
        }
        get_response.return_value = response

        with self.assertRaisesRegex(ValueError, "lacks options data"):
            fetch_chain("AAA", "2026-08-03", "redacted-test-key")

    def test_weekdays_exclude_weekend(self):
        self.assertEqual(["2026-07-20", "2026-07-21", "2026-07-22"], market_weekdays("2026-07-18", "2026-07-22"))

    def test_requests_cover_each_symbol_and_date(self):
        self.assertEqual(
            [("AAA", "2026-07-20"), ("BBB", "2026-07-20"), ("AAA", "2026-07-21"), ("BBB", "2026-07-21")],
            panel_requests(["AAA", "BBB"], "2026-07-20", "2026-07-21"),
        )

    def test_rejects_reversed_dates(self):
        with self.assertRaises(ValueError):
            market_weekdays("2026-07-22", "2026-07-20")

    def test_strips_utf8_bom_from_first_symbol(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "symbols.txt"
            path.write_text("\ufeffAAA\nBBB\n", encoding="utf-8")
            self.assertEqual(["AAA", "BBB"], read_symbols(path))


if __name__ == "__main__":
    unittest.main()
