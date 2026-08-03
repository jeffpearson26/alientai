import unittest

from alientai_v2.research.ai_semiconductor_narrative_features import (
    build_narrative_features,
)


class NarrativeFeatureTests(unittest.TestCase):
    def test_future_information_is_rejected(self):
        row = {"narrative_available_at_utc": "2026-08-03T14:01:00+00:00"}
        with self.assertRaises(ValueError):
            build_narrative_features(row, "2026-08-03T14:00:00+00:00")

    def test_exact_thesis_interactions_are_structured(self):
        row = {
            "narrative_available_at_utc": "2026-08-03T12:00:00+00:00",
            "ai_stack_role": "memory",
            "technical_ema50_distance_pct": 5.0,
            "return_20d_lag_pct": -8.0,
            "technical_rsi_14": 35.0,
            "fund_revenue_surprise_pct": 10.0,
            "fund_eps_surprise_pct": 12.0,
            "fund_guidance_midpoint_revision_pct": 8.0,
            "fund_ai_segment_growth_yoy_pct": 30.0,
            "fund_estimate_revision_30d_pct": 4.0,
            "analyst_net_upgrades_30d": 2,
            "industry_semiconductor_sales_growth_yoy_pct": 9.0,
            "industry_hbm_price_trend_pct": 5.0,
            "industry_hyperscaler_capex_revision_pct": 3.0,
            "catalyst_sessions_to_earnings": 4,
        }
        result = build_narrative_features(row, "2026-08-03T13:00:00+00:00")
        self.assertTrue(result["narrative_pullback_in_uptrend"])
        self.assertTrue(result["narrative_oversold_in_uptrend"])
        self.assertFalse(result["narrative_earnings_crosses_1d"])
        self.assertTrue(result["narrative_earnings_crosses_5d"])
        self.assertTrue(result["narrative_fundamental_demand_agreement"])
        self.assertTrue(result["narrative_upgrade_with_positive_estimate_revision"])
        self.assertTrue(result["narrative_role_memory"])

    def test_missing_values_are_explicit(self):
        result = build_narrative_features(
            {"narrative_available_at_utc": "2026-08-03T12:00:00+00:00"},
            "2026-08-03T13:00:00+00:00",
        )
        self.assertTrue(result["narrative_fund_revenue_surprise_pct_missing"])
        self.assertEqual(result["narrative_fund_revenue_surprise_pct"], 0.0)
        self.assertTrue(result["narrative_role_missing"])

    def test_unknown_role_fails_closed(self):
        with self.assertRaises(ValueError):
            build_narrative_features(
                {
                    "narrative_available_at_utc": "2026-08-03T12:00:00+00:00",
                    "ai_stack_role": "favorite_stock",
                },
                "2026-08-03T13:00:00+00:00",
            )


if __name__ == "__main__":
    unittest.main()
