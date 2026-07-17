from __future__ import annotations

import unittest

from alientai_v2.engines.similarity_engine import apply_main_buying_gate


class SimilarityMainBuyingGateTests(unittest.TestCase):
    def test_missing_setting_fails_closed(self):
        self.assertEqual("WATCH", apply_main_buying_gate("BUY_CANDIDATE", {}))

    def test_explicit_false_blocks_buy(self):
        self.assertEqual(
            "WATCH",
            apply_main_buying_gate(
                "BUY_CANDIDATE",
                {"similarity_engine_main_v2_buying_enabled": False},
            ),
        )

    def test_explicit_true_allows_buy(self):
        self.assertEqual(
            "BUY_CANDIDATE",
            apply_main_buying_gate(
                "BUY_CANDIDATE",
                {"similarity_engine_main_v2_buying_enabled": True},
            ),
        )

    def test_non_buy_decisions_are_unchanged(self):
        self.assertEqual("WATCH", apply_main_buying_gate("WATCH", {}))
        self.assertEqual("AVOID", apply_main_buying_gate("AVOID", {}))


if __name__ == "__main__":
    unittest.main()
