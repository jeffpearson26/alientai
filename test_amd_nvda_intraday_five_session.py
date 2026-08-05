from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from build_amd_nvda_intraday_five_session_panels import make_daily, resample_regular
from train_amd_nvda_intraday_call_five_session import select


class AmdNvdaFiveSessionTests(unittest.TestCase):
    def test_five_minute_resample_is_left_aligned(self) -> None:
        stamps = pd.date_range("2026-01-02 09:30", periods=6, freq="1min")
        frame = pd.DataFrame(
            {
                "timestamp": stamps,
                "open": [10, 11, 12, 13, 14, 15],
                "high": [11, 12, 13, 14, 15, 16],
                "low": [9, 10, 11, 12, 13, 14],
                "close": [10.5, 11.5, 12.5, 13.5, 14.5, 15.5],
                "volume": [1, 2, 3, 4, 5, 6],
                "market_date": ["2026-01-02"] * 6,
                "symbol": ["AMD"] * 6,
            }
        )
        bars = resample_regular(frame, "5min")
        self.assertEqual(list(bars["timestamp"]), [stamps[0], stamps[5]])
        self.assertEqual(float(bars.iloc[0]["open"]), 10.0)
        self.assertEqual(float(bars.iloc[0]["close"]), 14.5)
        self.assertEqual(float(bars.iloc[0]["volume"]), 15.0)

    def test_selector_can_abstain(self) -> None:
        rows = [
            {
                "symbol": "AMD",
                "market_date": "2026-01-02",
                "call_features_available": True,
                "call_activity_history_count": 20,
                "call_volume_unusual": True,
            },
            {
                "symbol": "NVDA",
                "market_date": "2026-01-02",
                "call_features_available": True,
                "call_activity_history_count": 20,
                "call_volume_unusual": True,
            },
        ]
        selected, dates = select(
            rows, np.asarray([0.49, 0.50]), require_calls=True
        )
        self.assertEqual(dates, 1)
        self.assertEqual(selected, [])

    def test_selector_requires_true_unusual_call(self) -> None:
        rows = [
            {
                "symbol": "AMD",
                "market_date": "2026-01-02",
                "call_features_available": True,
                "call_activity_history_count": 20,
                "call_volume_unusual": False,
            },
            {
                "symbol": "NVDA",
                "market_date": "2026-01-02",
                "call_features_available": False,
                "call_activity_history_count": None,
                "call_volume_unusual": None,
            },
        ]
        selected, _ = select(
            rows, np.asarray([0.90, 0.95]), require_calls=True
        )
        self.assertEqual(selected, [])

    def test_incomplete_session_is_excluded(self) -> None:
        stamps = pd.date_range("2026-01-02 09:30", periods=100, freq="1min")
        frame = pd.DataFrame(
            {
                "timestamp": stamps,
                "open": [10.0] * len(stamps),
                "high": [10.1] * len(stamps),
                "low": [9.9] * len(stamps),
                "close": [10.0] * len(stamps),
                "volume": [100] * len(stamps),
                "market_date": ["2026-01-02"] * len(stamps),
                "symbol": ["AMD"] * len(stamps),
            }
        )
        self.assertEqual(make_daily(frame, "1min"), [])


if __name__ == "__main__":
    unittest.main()
