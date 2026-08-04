import unittest

from alientai_v2.research.defined_risk_option_strategy import (
    OptionStrategyPolicy,
    OptionStrategyInputs,
    choose_defined_risk_strategy,
)


def inputs(**overrides):
    values = {
        "symbol": "NVDA",
        "stack_role": "merchant_accelerator",
        "direction_score": 0.75,
        "expected_absolute_move_pct": 7.0,
        "implied_move_pct": 5.0,
        "iv_rank": 0.50,
        "front_to_back_iv_ratio": 1.0,
        "technical_confirmation": 0.80,
        "range_bound_confidence": 0.20,
        "catalyst_within_five_sessions": True,
        "binary_event_within_five_sessions": False,
        "liquidity_score": 0.90,
    }
    values.update(overrides)
    return OptionStrategyInputs(**values)


class DefinedRiskOptionStrategyTests(unittest.TestCase):
    def test_policy_thresholds_are_explicit_and_validated(self):
        decision = choose_defined_risk_strategy(
            inputs(expected_absolute_move_pct=5.5, implied_move_pct=5.0),
            OptionStrategyPolicy(underpriced_move_ratio=1.05),
        )
        self.assertEqual(decision.strategy, "bull_call_debit_spread")
        with self.assertRaises(ValueError):
            choose_defined_risk_strategy(
                inputs(),
                OptionStrategyPolicy(
                    overpriced_move_ratio=1.3, underpriced_move_ratio=1.2
                ),
            )

    def test_bullish_underpriced_move_uses_call_debit_spread(self):
        result = choose_defined_risk_strategy(inputs())
        self.assertEqual(result.strategy, "bull_call_debit_spread")
        self.assertEqual(result.decision, "RESEARCH_CANDIDATE")
        self.assertFalse(result.execution_enabled)

    def test_direction_unknown_underpriced_move_uses_long_straddle(self):
        result = choose_defined_risk_strategy(inputs(direction_score=0.1))
        self.assertEqual(result.strategy, "long_straddle")

    def test_rich_iv_range_forecast_uses_iron_condor(self):
        result = choose_defined_risk_strategy(inputs(
            direction_score=0.1,
            expected_absolute_move_pct=3.0,
            implied_move_pct=5.0,
            iv_rank=0.8,
            range_bound_confidence=0.7,
        ))
        self.assertEqual(result.strategy, "iron_condor")

    def test_binary_event_blocks_short_volatility(self):
        result = choose_defined_risk_strategy(inputs(
            direction_score=0.1,
            expected_absolute_move_pct=3.0,
            implied_move_pct=5.0,
            iv_rank=0.8,
            range_bound_confidence=0.9,
            binary_event_within_five_sessions=True,
        ))
        self.assertEqual(result.decision, "ABSTAIN")

    def test_term_structure_can_choose_calendar(self):
        result = choose_defined_risk_strategy(inputs(
            direction_score=0.1,
            expected_absolute_move_pct=3.0,
            implied_move_pct=5.0,
            iv_rank=0.8,
            front_to_back_iv_ratio=1.25,
            range_bound_confidence=0.7,
        ))
        self.assertEqual(result.strategy, "calendar_spread")

    def test_emerging_specialist_is_half_sized(self):
        result = choose_defined_risk_strategy(inputs(
            symbol="CBRS",
            stack_role="emerging_inference_specialist",
        ))
        self.assertEqual(result.maximum_portfolio_risk_pct, 0.5)

    def test_low_liquidity_abstains(self):
        result = choose_defined_risk_strategy(inputs(liquidity_score=0.4))
        self.assertEqual(result.decision, "ABSTAIN")
        self.assertEqual(result.maximum_portfolio_risk_pct, 0.0)

    def test_invalid_role_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            choose_defined_risk_strategy(inputs(stack_role="favorite_stock"))


if __name__ == "__main__":
    unittest.main()
