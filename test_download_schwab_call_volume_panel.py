import unittest

from download_schwab_call_volume_panel import summarize_chain


class SchwabCallVolumePanelTests(unittest.TestCase):
    def test_sums_only_normalized_call_contracts(self):
        payload = {
            "symbol": "AAA",
            "underlyingPrice": 100.0,
            "callExpDateMap": {
                "2026-08-21:18": {
                    "100.0": [
                        {
                            "symbol": "AAA  260821C00100000",
                            "totalVolume": 20,
                            "openInterest": 40,
                            "bid": 1.0,
                            "ask": 1.1,
                        }
                    ],
                    "105.0": [
                        {
                            "symbol": "AAA  260821C00105000",
                            "totalVolume": 30,
                            "openInterest": 50,
                            "bid": 0.5,
                            "ask": 0.6,
                        }
                    ],
                }
            },
        }

        row = summarize_chain(payload, "AAA", "2026-08-03")

        self.assertEqual(50, row["option_call_volume"])
        self.assertEqual(90, row["option_call_open_interest"])
        self.assertEqual(2, row["call_contracts"])
        self.assertEqual("schwab_option_chain", row["source"])
        self.assertFalse(row["execution_enabled"])


if __name__ == "__main__":
    unittest.main()
