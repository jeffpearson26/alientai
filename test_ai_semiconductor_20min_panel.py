import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta

from build_ai_semiconductor_20min_panel import (
    intraday_label,
    replace_premarket,
    shift_prior_close_features,
    schwab_context,
    twenty_minute_label,
)
from evaluate_ai_semiconductor_intraday_daily_policy import daily_policy_metrics
import numpy as np


class TwentyMinutePanelTests(unittest.TestCase):
    def test_schwab_premarket_replaces_existing_provider_values(self):
        source = {
            "symbol": "NVDA",
            "market_date": "2026-08-03",
            "model_premarket_gap_pct": 999,
            "technical_rsi_2": 10,
        }
        candles = [
            {
                "timestamp": "2026-08-02 16:00:00",
                "open": 99,
                "high": 100,
                "low": 98,
                "close": 100,
                "volume": 10,
            },
            {
                "timestamp": "2026-08-03 09:25:00",
                "open": 101,
                "high": 102,
                "low": 100,
                "close": 102,
                "volume": 20,
            },
        ]
        result = replace_premarket(source, candles, "2026-08-03")
        self.assertAlmostEqual(result["model_premarket_gap_pct"], 2.0)
        self.assertEqual(result["technical_rsi_2"], 10)
        self.assertEqual(result["model_premarket_last_timestamp_et"], "2026-08-03 09:25:00")

    def test_schwab_context_converts_utc_to_eastern_and_keeps_prior_history(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "NVDA_schwab_5m_max.csv"
            path.write_text(
                "symbol,datetime_ms,datetime_utc,open,high,low,close,volume\n"
                "NVDA,1,2026-08-02T13:25:00+00:00,99,100,98,99.5,50\n"
                "NVDA,2,2026-08-03T13:25:00+00:00,100,101,99,100.5,75\n"
                "NVDA,3,2026-08-03T13:35:00+00:00,101,102,100,101.5,100\n",
                encoding="utf-8",
            )
            rows = schwab_context(Path(directory), "NVDA", "2026-08-03")
        self.assertEqual(
            [row["timestamp"] for row in rows],
            [
                "2026-08-02 09:25:00",
                "2026-08-03 09:25:00",
                "2026-08-03 09:35:00",
            ],
        )

    def test_late_entry_uses_first_safe_next_bar(self):
        rows = [
            {
                "timestamp": f"2026-08-03 {stamp}:00",
                "open": open_price,
                "close": close_price,
            }
            for stamp, open_price, close_price in (
                ("09:30", 99, 100),
                ("09:35", 101, 102),
                ("09:40", 102, 103),
                ("09:45", 103, 104),
                ("09:50", 104, 106),
            )
        ]
        result = intraday_label(rows, "2026-08-03", 20, "09:35")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["label_entry_0935_open"], 101)
        self.assertEqual(result["label_exit_0950_close"], 106)
        self.assertEqual(
            result["label_entry_timestamp_et"],
            "2026-08-03 09:35:00",
        )
        self.assertEqual(
            result["label_exit_timestamp_et"],
            "2026-08-03 09:55:00",
        )

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
