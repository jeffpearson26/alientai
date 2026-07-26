from __future__ import annotations

import unittest

from alientai_v2.research.selective_five_day_policy import (
    POLICY_ID,
    evaluate_selective_five_day_panel,
)


POLICY = {
    "minimum_universe_size": 3,
    "minimum_profit_probability": 0.60,
    "minimum_large_move_probability": 0.30,
    "minimum_expected_net_return_pct": 0.75,
    "minimum_lower_quantile_net_return_pct": -4.0,
    "maximum_model_disagreement": 0.12,
    "round_trip_cost_pct": 0.25,
}


def row(symbol: str, **overrides):
    result = {
        "symbol": symbol,
        "market_date": "2026-07-24",
        "data_complete": True,
        "technical_options_agree": True,
        "calibrated_profit_probability": 0.70,
        "calibrated_large_move_probability": 0.40,
        "expected_net_return_pct": 1.25,
        "lower_quantile_net_return_pct": -2.0,
        "model_disagreement": 0.05,
    }
    result.update(overrides)
    return result


class SelectiveFiveDayPolicyTests(unittest.TestCase):
    def test_keeps_every_independently_qualified_candidate(self):
        result = evaluate_selective_five_day_panel(
            [
                row("AAA", calibrated_profit_probability=0.72),
                row("BBB", calibrated_profit_probability=0.81),
                row("CCC", calibrated_profit_probability=0.75),
            ],
            POLICY,
        )
        self.assertEqual("RESEARCH_CANDIDATES", result["status"])
        self.assertEqual(["BBB", "CCC", "AAA"], [item["symbol"] for item in result["candidates"]])
        self.assertTrue(all(item["decision"] == "AVOID" for item in result["candidates"]))
        self.assertTrue(all(item["engine_id"] == POLICY_ID for item in result["candidates"]))

    def test_abstains_when_no_row_clears_all_gates(self):
        result = evaluate_selective_five_day_panel(
            [
                row("AAA", technical_options_agree=False),
                row("BBB", expected_net_return_pct=0.20),
                row("CCC", model_disagreement=0.30),
            ],
            POLICY,
        )
        self.assertEqual("ABSTAIN", result["status"])
        self.assertEqual([], result["candidates"])
        self.assertEqual(3, len(result["rejections"]))

    def test_missing_score_fails_closed(self):
        source = row("AAA")
        source.pop("lower_quantile_net_return_pct")
        result = evaluate_selective_five_day_panel([source, row("BBB"), row("CCC")], POLICY)
        rejected = next(item for item in result["rejections"] if item["symbol"] == "AAA")
        self.assertIn("missing lower_quantile_net_return_pct", rejected["reasons"])

    def test_incomplete_universe_produces_no_candidates(self):
        result = evaluate_selective_five_day_panel([row("AAA"), row("BBB")], POLICY)
        self.assertEqual("INCOMPLETE_PANEL", result["status"])
        self.assertEqual([], result["candidates"])
        self.assertFalse(result["execution_enabled"])

    def test_rejects_mixed_dates_and_duplicate_symbols(self):
        with self.assertRaises(ValueError):
            evaluate_selective_five_day_panel(
                [row("AAA"), row("BBB", market_date="2026-07-25"), row("CCC")],
                POLICY,
            )
        with self.assertRaises(ValueError):
            evaluate_selective_five_day_panel([row("AAA"), row("AAA"), row("CCC")], POLICY)

    def test_requires_frozen_policy_thresholds(self):
        invalid = dict(POLICY)
        invalid.pop("minimum_profit_probability")
        with self.assertRaises(ValueError):
            evaluate_selective_five_day_panel([row("AAA"), row("BBB"), row("CCC")], invalid)


if __name__ == "__main__":
    unittest.main()
