from __future__ import annotations

import unittest

from capture_schwab_shadow_calls import normalize_chain
from shadow_call_options import OptionChainError


class SchwabShadowCallTests(unittest.TestCase):
    def test_normalizes_required_contract_fields(self) -> None:
        chain = {
            "symbol": "NVDA",
            "callExpDateMap": {
                "2026-08-21:21": {
                    "200.0": [{
                        "symbol": "NVDA  260821C00200000",
                        "bid": 8.0, "ask": 8.2, "bidSize": 10, "askSize": 20,
                        "totalVolume": 400, "openInterest": 1200,
                        "delta": 0.66, "volatility": 42.0,
                    }]
                }
            },
        }
        row = normalize_chain(chain, "NVDA")[0]
        self.assertEqual(row["contractID"], "NVDA  260821C00200000")
        self.assertEqual(row["open_interest"], 1200)
        self.assertEqual(row["expiration"], "2026-08-21")

    def test_rejects_wrong_underlying(self) -> None:
        with self.assertRaisesRegex(OptionChainError, "unexpected"):
            normalize_chain({"symbol": "AMD", "callExpDateMap": {}}, "NVDA")


if __name__ == "__main__":
    unittest.main()
