from __future__ import annotations

import unittest

from alientai_v2.research.contextual_options_shadow_policy import POLICY_ID, select_shadow_candidates


class ContextualOptionsShadowPolicyTests(unittest.TestCase):
    def test_selects_only_unusual_calls_in_top_context(self):
        rows = [
            {"symbol": "AAA", "market_date": "2026-07-23", "technical_context_score": 0.1, "call_volume_unusual": True},
            {"symbol": "BBB", "market_date": "2026-07-23", "technical_context_score": 0.7, "call_volume_unusual": False},
            {"symbol": "CCC", "market_date": "2026-07-23", "technical_context_score": 0.8, "call_volume_unusual": True},
            {"symbol": "DDD", "market_date": "2026-07-23", "technical_context_score": 1.0, "call_volume_unusual": True},
        ]
        result = select_shadow_candidates(rows, top_fraction=0.5)
        self.assertEqual(["DDD", "CCC"], [row["symbol"] for row in result])
        self.assertEqual("AVOID", result[0]["decision"])
        self.assertEqual("BUY_CANDIDATE", result[0]["shadow_research_decision"])
        self.assertEqual(POLICY_ID, result[0]["engine_id"])

    def test_rejects_mixed_market_dates(self):
        rows = [
            {"symbol": "AAA", "market_date": "2026-07-23", "technical_context_score": 0.8, "call_volume_unusual": True},
            {"symbol": "BBB", "market_date": "2026-07-24", "technical_context_score": 0.9, "call_volume_unusual": True},
        ]
        with self.assertRaises(ValueError):
            select_shadow_candidates(rows)


if __name__ == "__main__":
    unittest.main()
