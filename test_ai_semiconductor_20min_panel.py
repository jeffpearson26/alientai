import unittest
from datetime import datetime, timedelta

from build_ai_semiconductor_20min_panel import intraday_label, shift_prior_close_features, twenty_minute_label
from evaluate_ai_semiconductor_intraday_daily_policy import daily_policy_metrics
import numpy as np


class TwentyMinutePanelTests(unittest.TestCase):
    def test_label_uses_0930_open_and_0945_close(self):
        rows = [
            {"timestamp": "2026-01-05 09:30:00", "open": "100", "close": "101"},
            {"timestamp": "2026-01-05 09:35:00", "open": "101", "close": "102"},
            {"timestamp": "2026-01-05 09:40:00", "open": "102", "close": "103"},
            {"timestamp": "2026-01-05 09:45:00", "open": "103", "close": "104"},
        ]
        result = twenty_minute_label(rows, "2026-01-05")
        self.assertAlmostEqual(result["label_forward_return_20m_gross_pct"], 4.0)
        self.assertAlmostEqual(result["label_forward_return_20m_net_pct"], 3.75)

    def test_missing_intermediate_bar_fails_closed(self):
        rows = [
            {"timestamp": "2026-01-05 09:30:00", "open": "100", "close": "101"},
            {"timestamp": "2026-01-05 09:45:00", "open": "103", "close": "104"},
        ]
        self.assertIsNone(twenty_minute_label(rows, "2026-01-05"))

    def test_sixty_minute_label_uses_1025_bar_close(self):
        rows = []
        start = datetime.strptime("09:30", "%H:%M")
        for index in range(12):
            stamp = (start + timedelta(minutes=5 * index)).strftime("%H:%M")
            rows.append({
                "timestamp": f"2026-01-05 {stamp}:00",
                "open": "100",
                "close": "106" if stamp == "10:25" else "100",
            })
        result = intraday_label(rows, "2026-01-05", 60)
        self.assertAlmostEqual(result["label_forward_return_60m_gross_pct"], 6.0)
        self.assertAlmostEqual(result["label_forward_return_60m_net_pct"], 5.75)
        self.assertEqual(result["label_exit_timestamp_et"], "2026-01-05 10:30:00")

    def test_close_features_are_shifted_from_immediately_prior_session(self):
        rows = [
            {"symbol": "NVDA", "market_date": "2026-01-05", "technical_rsi_2": 10, "model_call_volume_unusual": 0, "model_premarket_gap_pct": 1},
            {"symbol": "NVDA", "market_date": "2026-01-06", "technical_rsi_2": 90, "model_call_volume_unusual": 1, "model_premarket_gap_pct": 2},
        ]
        shifted, missing = shift_prior_close_features(
            rows, {"NVDA": ["2026-01-05", "2026-01-06"]}
        )
        self.assertEqual(missing, 1)
        self.assertEqual(shifted[0]["technical_rsi_2"], 10)
        self.assertEqual(shifted[0]["model_call_volume_unusual"], 0)
        self.assertEqual(shifted[0]["model_premarket_gap_pct"], 2)
        self.assertEqual(shifted[0]["prior_feature_market_date"], "2026-01-05")

    def test_gap_in_source_panel_fails_closed(self):
        rows = [
            {"symbol": "NVDA", "market_date": "2026-01-05", "technical_rsi_2": 10},
            {"symbol": "NVDA", "market_date": "2026-01-07", "technical_rsi_2": 90},
        ]
        shifted, missing = shift_prior_close_features(
            rows, {"NVDA": ["2026-01-05", "2026-01-06", "2026-01-07"]}
        )
        self.assertEqual(shifted, [])
        self.assertEqual(missing, 2)

    def test_daily_policy_ranks_within_each_date(self):
        rows = [
            {"market_date": "2026-01-05", "symbol": "A", "r": 1.0},
            {"market_date": "2026-01-05", "symbol": "B", "r": -1.0},
            {"market_date": "2026-01-06", "symbol": "A", "r": -2.0},
            {"market_date": "2026-01-06", "symbol": "B", "r": 2.0},
        ]
        result = daily_policy_metrics(rows, np.asarray([0.9, 0.1, 0.1, 0.9]), "r", 0.5)
        self.assertEqual(result["trades"], 2)
        self.assertEqual(result["positive_trade_rate"], 1.0)
        self.assertEqual(result["mean_daily_net_return_pct"], 1.5)


if __name__ == "__main__":
    unittest.main()
