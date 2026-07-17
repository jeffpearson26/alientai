from __future__ import annotations

import unittest

from alientai_v2.engine import engine_main_buying_rejection


class EngineMainBuyingAllowlistTests(unittest.TestCase):
    def test_missing_allowlist_fails_closed(self):
        reason = engine_main_buying_rejection({"engine_id": "prediction_friday"}, {})
        self.assertIn("research-only", reason)

    def test_empty_allowlist_rejects_every_engine(self):
        reason = engine_main_buying_rejection(
            {"engine_id": "prediction_20day"},
            {"main_account_enabled_buy_engines": []},
        )
        self.assertIn("prediction_20day", reason)

    def test_explicitly_allowlisted_engine_is_approved_by_gate(self):
        reason = engine_main_buying_rejection(
            {"engine_id": "validated_engine"},
            {"main_account_enabled_buy_engines": ["validated_engine"]},
        )
        self.assertEqual("", reason)

    def test_blank_engine_fails_closed(self):
        reason = engine_main_buying_rejection(
            {"engine_id": ""},
            {"main_account_enabled_buy_engines": ["prediction_friday"]},
        )
        self.assertIn("unknown_engine", reason)


if __name__ == "__main__":
    unittest.main()
