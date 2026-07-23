from __future__ import annotations

import unittest

from download_alpha_vantage_option_panel import market_weekdays, panel_requests


class OptionPanelDownloaderTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
