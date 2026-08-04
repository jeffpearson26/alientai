import unittest

from alientai_v2.research.catalyst_momentum_5d import engineer_rows
from train_ai_semiconductor_catalyst_momentum_5d import (
    choose_fraction,
    metrics,
    select_rows,
)


def base_row(symbol="AAA", market_date="2026-01-02"):
    return {
        "symbol": symbol,
        "market_date": market_date,
        "label_entry_market_date": "2026-01-05",
        "label_5d_exit_market_date": "2026-01-09",
        "label_5d_net_return_pct": 3.0,
        "label_1d_net_return_pct": 0.5,
        "return_20d_lag_pct": 5.0,
        "return_60d_lag_pct": 10.0,
        "technical_rsi_2": 5.0,
        "technical_rsi_14": 34.0,
        "technical_bollinger_position": 0.2,
        "technical_ema9_distance_pct": -0.5,
        "technical_ema21_distance_pct": 1.0,
        "technical_ema50_distance_pct": 2.0,
        "technical_macd_histogram_pct": 0.1,
        "technical_latest_relative_volume_20": 1.3,
        "technical_obv_change_10d_normalized": 1.0,
        "technical_atr14_pct": 3.0,
        "narrative_news_1d_article_count": 3,
        "narrative_news_1d_mean_relevance": 0.7,
        "narrative_news_1d_weighted_sentiment": 0.2,
        "model_analyst_proxy_event_count_14d": 0,
        "model_analyst_proxy_net_action_5d": 0,
    }


class CatalystMomentumFiveDayTests(unittest.TestCase):
    def test_material_news_and_oversold_setup_are_eligible(self):
        result = engineer_rows([base_row()])[0]
        self.assertTrue(result["cm_technical_oversold_bounce"])
        self.assertTrue(result["cm_catalyst_material_target_news"])
        self.assertTrue(result["cm_primary_eligible"])

    def test_parabolic_name_fails_risk_gate(self):
        row = base_row()
        row["technical_rsi_14"] = 92.0
        result = engineer_rows([row])[0]
        self.assertTrue(result["cm_risk_parabolic"])
        self.assertFalse(result["cm_primary_eligible"])

    def test_negative_analyst_overlay_fails_primary_gate(self):
        row = base_row()
        row["model_analyst_proxy_net_action_5d"] = -1
        result = engineer_rows([row])[0]
        self.assertTrue(result["cm_fundamental_obvious_negative"])
        self.assertFalse(result["cm_primary_eligible"])

    def test_relative_strength_rank_is_cross_sectional_and_lagged(self):
        weak = base_row("AAA")
        strong = base_row("BBB")
        weak["return_20d_lag_pct"] = -5
        strong["return_20d_lag_pct"] = 8
        results = {row["symbol"]: row for row in engineer_rows([weak, strong])}
        self.assertEqual(results["AAA"]["cm_technical_return20_rank"], 0.0)
        self.assertEqual(results["BBB"]["cm_technical_return20_rank"], 1.0)

    def test_missing_relative_strength_is_not_ranked_as_zero(self):
        missing = base_row("MISSING")
        weak = base_row("WEAK")
        missing["return_20d_lag_pct"] = None
        weak["return_20d_lag_pct"] = -5.0
        results = {row["symbol"]: row for row in engineer_rows([missing, weak])}
        self.assertIsNone(results["MISSING"]["cm_technical_return20_rank"])
        self.assertFalse(results["MISSING"]["cm_technical_return20_available"])
        self.assertEqual(results["WEAK"]["cm_technical_return20_rank"], 0.0)

    def test_selection_requires_eligibility_and_respects_daily_maximum(self):
        rows = []
        for index in range(8):
            row = base_row(f"S{index}")
            row["cm_primary_eligible"] = index < 7
            rows.append(row)
        selected = select_rows(rows, list(range(8)), 1.0, "cm_primary_eligible")
        self.assertEqual(len(selected), 5)
        self.assertNotIn("S7", {row["symbol"] for row in selected})

    def test_fraction_is_selected_from_validation_metrics_only(self):
        results = {
            "0.1": {"count": 30, "distinct_market_dates": 10,
                    "validation_score": 0.8, "fifth_percentile_pct": -2.0,
                    "win_rate": 0.6},
            "0.2": {"count": 35, "distinct_market_dates": 12,
                    "validation_score": 1.0, "fifth_percentile_pct": -3.0,
                    "win_rate": 0.5},
            "0.3": {"count": 29, "distinct_market_dates": 15,
                    "validation_score": 9.0, "fifth_percentile_pct": 4.0,
                    "win_rate": 1.0},
        }
        self.assertEqual(choose_fraction(results), 0.2)

    def test_one_day_time_stop_is_fixed_and_not_a_selection_target(self):
        stopped = base_row("STOP")
        stopped["label_1d_net_return_pct"] = -1.0
        stopped["label_5d_net_return_pct"] = -8.0
        held = base_row("HOLD")
        held["label_1d_net_return_pct"] = 1.0
        held["label_5d_net_return_pct"] = 4.0
        result = metrics([stopped, held])
        self.assertEqual(result["mean_net_return_pct"], -2.0)
        self.assertEqual(
            result["one_day_nonpositive_time_stop"]["mean_net_return_pct"],
            1.5,
        )


if __name__ == "__main__":
    unittest.main()
