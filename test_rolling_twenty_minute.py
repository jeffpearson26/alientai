from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from alientai_v2.research.rolling_twenty_minute import (
    NEW_YORK,
    build_features_at,
    build_label_at,
    build_model_features_at,
    build_observation_at,
    latest_completed_bar_start,
)
from compile_rolling_twenty_minute_panel import build_feature_frame, feature_names


def candles(count: int = 390) -> list[dict[str, object]]:
    start = datetime(2026, 7, 31, 9, 30)
    output = []
    for index in range(count):
        price = 100.0 + index * 0.1
        output.append(
            {
                "timestamp": (start + timedelta(minutes=index)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "open": price - 0.02,
                "high": price + 0.05,
                "low": price - 0.05,
                "close": price,
                "volume": 1000 + index,
            }
        )
    return output


class RollingTwentyMinuteTests(unittest.TestCase):
    def test_mid_minute_query_uses_last_fully_completed_bar(self) -> None:
        captured = datetime(2026, 7, 31, 10, 17, 38, tzinfo=NEW_YORK)
        self.assertEqual(
            latest_completed_bar_start(captured),
            datetime(2026, 7, 31, 10, 16, tzinfo=NEW_YORK),
        )

    def test_twentieth_subsequent_close_is_exact_target(self) -> None:
        rows = candles()
        feature_start = datetime(2026, 7, 31, 10, 0, tzinfo=NEW_YORK)
        result = build_label_at(rows, feature_start)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["label_effective_as_of_et"], "2026-07-31T10:01:00-04:00")
        self.assertEqual(result["label_entry_at_et"], "2026-07-31T10:01:00-04:00")
        self.assertEqual(result["label_target_at_et"], "2026-07-31T10:21:00-04:00")
        self.assertAlmostEqual(result["label_entry_open"], 103.08)
        self.assertAlmostEqual(result["label_target_close"], 105.0)
        self.assertEqual(result["entry_assumption"], "next_minute_open")

    def test_late_observation_does_not_cross_regular_close(self) -> None:
        rows = candles()
        result = build_label_at(
            rows,
            datetime(2026, 7, 31, 15, 40, tzinfo=NEW_YORK),
        )
        self.assertIsNone(result)

    def test_missing_future_minute_fails_closed(self) -> None:
        rows = [
            row
            for row in candles()
            if row["timestamp"] != "2026-07-31 10:10:00"
        ]
        result = build_label_at(
            rows,
            datetime(2026, 7, 31, 10, 0, tzinfo=NEW_YORK),
        )
        self.assertIsNone(result)

    def test_features_do_not_change_when_future_prices_change(self) -> None:
        rows = candles()
        feature_start = datetime(2026, 7, 31, 10, 0, tzinfo=NEW_YORK)
        before = build_features_at(rows, feature_start)
        for row in rows:
            if str(row["timestamp"]) > "2026-07-31 10:00:00":
                row["close"] = float(row["close"]) * 10.0
                row["high"] = max(float(row["high"]), float(row["close"]))
        after = build_features_at(rows, feature_start)
        self.assertEqual(before, after)

    def test_missing_history_minute_is_not_mislabeled_as_exact_lag(self) -> None:
        rows = [
            row
            for row in candles()
            if row["timestamp"] != "2026-07-31 09:59:00"
        ]
        result = build_features_at(
            rows,
            datetime(2026, 7, 31, 10, 0, tzinfo=NEW_YORK),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertFalse(result["history_1m_available"])
        self.assertIsNone(result["return_1m_pct"])

    def test_live_model_features_exactly_match_compiler_features(self) -> None:
        rows = candles()
        captured = datetime(2026, 7, 31, 10, 1, 30, tzinfo=NEW_YORK)
        result = build_model_features_at(rows, rows, rows, captured)
        self.assertIsNotNone(result)
        assert result is not None
        frames = []
        for _ in range(3):
            frame = pd.DataFrame(rows)
            frame["timestamp"] = pd.to_datetime(frame["timestamp"])
            frames.append(frame)
        compiled = build_feature_frame(*frames)
        expected = compiled[
            compiled["timestamp"] == datetime(2026, 7, 31, 10, 0)
        ].iloc[0]
        self.assertEqual(result["feature_names"], feature_names())
        for name in feature_names():
            actual = result["features"][name]
            expected_value = expected[name]
            if actual is None:
                self.assertTrue(pd.isna(expected_value))
            else:
                self.assertAlmostEqual(actual, float(expected_value), places=6)

    def test_observation_is_research_only(self) -> None:
        result = build_observation_at(
            candles(),
            datetime(2026, 7, 31, 15, 39, tzinfo=ZoneInfo("America/New_York")),
            horizon_minutes=20,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result["research_only"])
        self.assertFalse(result["execution_enabled"])


if __name__ == "__main__":
    unittest.main()
