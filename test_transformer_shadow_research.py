from __future__ import annotations

import unittest

from alientai_v2.engines.transformer_20day import (
    score_to_decision,
    transformer_shadow_research_decision,
)


class TransformerShadowResearchTests(unittest.TestCase):
    def setUp(self):
        self.allowed = {"policy": "ALLOW_BUY"}

    def test_probability_at_shadow_threshold_is_journal_candidate(self):
        result = transformer_shadow_research_decision(0.55, self.allowed, {})
        self.assertEqual("BUY_CANDIDATE", result)

    def test_shadow_threshold_does_not_lower_execution_threshold(self):
        decision, _, _ = score_to_decision("NVDA", 0.55, self.allowed, {})
        self.assertEqual("AVOID", decision)
        self.assertEqual(
            "BUY_CANDIDATE",
            transformer_shadow_research_decision(0.55, self.allowed, {}),
        )

    def test_blocked_policy_is_not_journaled(self):
        result = transformer_shadow_research_decision(
            0.90,
            {"policy": "BLOCK_BUY"},
            {},
        )
        self.assertEqual("", result)

    def test_shadow_research_can_be_disabled(self):
        settings = {"transformer_20day_shadow_research_enabled": False}
        result = transformer_shadow_research_decision(0.90, self.allowed, settings)
        self.assertEqual("", result)


if __name__ == "__main__":
    unittest.main()
