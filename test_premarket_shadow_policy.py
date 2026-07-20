from __future__ import annotations

import unittest

from build_premarket_shadow_policy import build_policy


class PremarketShadowPolicyTests(unittest.TestCase):
    def test_hold_fails_closed(self):
        policy = build_policy({"promotion_gate": {"status": "NATURAL_UNIVERSE_HOLD"}}, {})
        self.assertEqual(policy["status"], "RESEARCH_HOLD")
        self.assertFalse(policy["shadow_recording_enabled"])
        self.assertFalse(policy["execution_enabled"])
        self.assertFalse(policy["paper_buying_enabled"])

    def test_pass_selects_strictest_passing_slice_but_never_execution(self):
        report = {
            "promotion_gate": {
                "status": "NATURAL_UNIVERSE_PASS",
                "checks": [
                    {"selection": "top_0.0100", "passed": True},
                    {"selection": "top_0.0025", "passed": True},
                    {"selection": "top_0.0010", "passed": False},
                ],
            }
        }
        ablation = {"experiments": [{
            "name": "technical_plus_premarket", "model_path": "combined.txt", "model_features": ["x"],
        }]}
        policy = build_policy(report, ablation)
        self.assertEqual(policy["status"], "PROSPECTIVE_SHADOW_APPROVED")
        self.assertEqual(policy["selection"], "top_0.0025")
        self.assertEqual(policy["maximum_daily_universe_fraction"], 0.0025)
        self.assertTrue(policy["shadow_recording_enabled"])
        self.assertFalse(policy["execution_enabled"])
        self.assertFalse(policy["paper_buying_enabled"])
        self.assertFalse(policy["live_trading_enabled"])

    def test_pass_without_combined_model_holds(self):
        report = {"promotion_gate": {
            "status": "NATURAL_UNIVERSE_PASS", "checks": [{"selection": "top_0.0010", "passed": True}],
        }}
        self.assertEqual(build_policy(report, {})["status"], "RESEARCH_HOLD")


if __name__ == "__main__":
    unittest.main()
