import unittest

from alientai_v2.alpha_vantage_quote_client import parse_bulk_quote_payload


class AlphaVantageQuoteClientTests(unittest.TestCase):
    def test_normalizes_bulk_quote_rows(self):
        rows = parse_bulk_quote_payload({"data": [{
            "symbol": "AAPL", "close": "200.50", "previous_close": "198.00",
            "change_percent": "1.2626%", "volume": "123456",
            "bid_price": "200.45", "ask_price": "200.55", "timestamp": "2026-07-30T16:00:00Z",
        }]})
        self.assertEqual(rows[0]["symbol"], "AAPL")
        self.assertEqual(rows[0]["price"], 200.5)
        self.assertEqual(rows[0]["net_change_percent"], 1.2626)
        self.assertEqual(rows[0]["source"], "alpha_vantage_realtime_bulk_quote")

    def test_rejects_provider_message_without_rows(self):
        with self.assertRaisesRegex(RuntimeError, "rate limit"):
            parse_bulk_quote_payload({"Information": "rate limit"})

    def test_rejects_unusable_rows(self):
        with self.assertRaisesRegex(RuntimeError, "usable prices"):
            parse_bulk_quote_payload({"data": [{"symbol": "AAPL", "close": "0"}]})


if __name__ == "__main__":
    unittest.main()
