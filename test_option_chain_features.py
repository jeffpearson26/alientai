from __future__ import annotations

import unittest

from alientai_v2.features.option_chain_features import option_chain_features


class OptionChainFeatureTests(unittest.TestCase):
    def test_aggregates_pre_move_chain_without_outcomes(self):
        chain = [
            {"type": "call", "strike": "100", "bid": "4.8", "ask": "5.0", "volume": "200", "open_interest": "1000", "implied_volatility": "0.30"},
            {"type": "put", "strike": "100", "bid": "3.8", "ask": "4.0", "volume": "100", "open_interest": "800", "implied_volatility": "0.35"},
        ]
        result = option_chain_features(chain, 100)
        self.assertEqual(result["option_put_call_volume_ratio"], 0.5)
        self.assertEqual(result["option_put_call_open_interest_ratio"], 0.8)
        self.assertAlmostEqual(result["option_volume_open_interest_ratio"], 300 / 1800)
        self.assertAlmostEqual(result["option_near_money_put_call_iv_skew"], 0.05)

    def test_zero_denominators_are_missing(self):
        result = option_chain_features([{"type": "put", "strike": "100"}], 100)
        self.assertIsNone(result["option_put_call_volume_ratio"])
        self.assertIsNone(result["option_volume_open_interest_ratio"])


if __name__ == "__main__":
    unittest.main()
