from __future__ import annotations

import unittest

from shadow_call_options import (
    OptionChainError,
    conservative_option_return_pct,
    select_call,
    validate_realtime_payload,
)


class ShadowCallOptionTests(unittest.TestCase):
    def test_rejects_artificial_provider_payload(self) -> None:
        with self.assertRaisesRegex(OptionChainError, "artificial"):
            validate_realtime_payload(
                {"message": "SAMPLE DATA SCHEMA IS ARTIFICIAL", "data": [{"symbol": "NVDA"}]},
                "NVDA",
            )

    def test_selects_liquid_call_deterministically(self) -> None:
        common = {
            "symbol": "NVDA", "date": "2026-07-31", "type": "call",
            "expiration": "2026-08-21", "strike": "180", "volume": "500",
        }
        rows = [
            {**common, "contractID": "WIDE", "bid": "9", "ask": "10", "delta": ".67", "open_interest": "5000"},
            {**common, "contractID": "LIQUID", "bid": "9.8", "ask": "10", "delta": ".66", "open_interest": "1000"},
            {**common, "contractID": "LOW_OI", "bid": "9.9", "ask": "10", "delta": ".68", "open_interest": "10"},
            {**common, "contractID": "PUT", "type": "put", "bid": "9.9", "ask": "10", "delta": "-.68", "open_interest": "5000"},
        ]
        self.assertEqual(select_call(rows, "2026-07-31")["contractID"], "LIQUID")

    def test_fails_closed_without_eligible_call(self) -> None:
        with self.assertRaisesRegex(OptionChainError, "no call"):
            select_call([], "2026-07-31")

    def test_conservative_fill_uses_ask_then_bid(self) -> None:
        self.assertAlmostEqual(conservative_option_return_pct(2.0, 2.5), 25.0)


if __name__ == "__main__":
    unittest.main()
