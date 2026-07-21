from __future__ import annotations

import unittest

from download_alpha_vantage_event_news import provider_ticker


class AlphaVantageEventNewsTests(unittest.TestCase):
    def test_provider_ticker_preserves_normal_symbol(self):
        self.assertEqual("NVDA", provider_ticker("nvda"))

    def test_provider_ticker_translates_share_class_dot(self):
        self.assertEqual("BRK-B", provider_ticker("BRK.B"))


if __name__ == "__main__":
    unittest.main()
