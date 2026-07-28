from __future__ import annotations

import unittest

from alientai_v2.features.afterhours_features import build_afterhours_features
from evaluate_afterhours_premarket_continuation import (
    afterhours_from_index,
    directional_features,
    evaluate,
    signed_volume_proxy,
)
from evaluate_selective_premarket_same_day import same_day_net_return


def candle(stamp: str, close: float, volume: float = 100.0) -> dict[str, object]:
    return {
        "timestamp": stamp, "open": close, "high": close,
        "low": close, "close": close, "volume": volume,
    }


class AfterhoursPremarketTests(unittest.TestCase):
    def test_afterhours_uses_latest_completed_session_and_prior_baseline(self) -> None:
        rows = [
            candle("2026-07-20 16:00:00", 100),
            candle("2026-07-20 16:05:00", 101, 50),
            candle("2026-07-20 19:55:00", 102, 50),
            candle("2026-07-21 16:00:00", 110),
            candle("2026-07-21 16:05:00", 111, 200),
            candle("2026-07-21 19:55:00", 112, 200),
            candle("2026-07-22 16:05:00", 999, 10000),
        ]
        result = build_afterhours_features(rows, "2026-07-22")
        indexed = afterhours_from_index({
            day: [row for row in rows if str(row["timestamp"]).startswith(day)]
            for day in ("2026-07-20", "2026-07-21", "2026-07-22")
        }, "2026-07-22")
        self.assertTrue(result["afterhours_available"])
        self.assertEqual(result["afterhours_session_date"], "2026-07-21")
        self.assertEqual(result["afterhours_relative_volume"], 4.0)
        self.assertEqual(indexed["afterhours_relative_volume"], result["afterhours_relative_volume"])
        self.assertAlmostEqual(result["afterhours_last_vs_regular_close_pct"], 100 * (112 / 110 - 1))

    def test_same_day_label_requires_open_and_close_bars(self) -> None:
        complete = [
            candle("2026-07-22 09:30:00", 100),
            candle("2026-07-22 16:00:00", 102),
        ]
        self.assertAlmostEqual(same_day_net_return(complete, "2026-07-22"), 1.75)
        self.assertIsNone(same_day_net_return(complete[:1], "2026-07-22"))

    def test_joint_threshold_requires_both_sessions(self) -> None:
        base = {
            "afterhours_available": True, "premarket_available": True,
            "net_return_pct": 1.0,
        }
        rows = [
            {**base, "afterhours_relative_volume": 3.0, "premarket_relative_volume": 3.0},
            {**base, "afterhours_relative_volume": 3.0, "premarket_relative_volume": 1.0},
        ]
        result = evaluate(rows)["fixed_thresholds"]["at_least_2x"]
        self.assertEqual(result["afterhours_only"]["rows"], 2)
        self.assertEqual(result["joint"]["rows"], 1)

    def test_signed_volume_proxy_separates_rising_and_falling_bars(self) -> None:
        rows = [candle("2026-07-22 04:00:00", 101, 200), candle("2026-07-22 04:05:00", 100, 50)]
        result = signed_volume_proxy(rows, 100)
        self.assertEqual(result["buy_volume_proxy"], 200)
        self.assertEqual(result["sell_volume_proxy"], 50)
        self.assertEqual(result["buy_share_proxy"], 0.8)

    def test_directional_features_use_only_prior_baselines(self) -> None:
        by_date = {
            "2026-07-19": [candle("2026-07-19 16:00:00", 100)],
            "2026-07-20": [
                candle("2026-07-20 04:00:00", 101, 10),
                candle("2026-07-20 16:00:00", 100),
                candle("2026-07-20 16:05:00", 101, 10),
            ],
            "2026-07-21": [
                candle("2026-07-21 04:00:00", 102, 30),
                candle("2026-07-21 16:00:00", 100),
                candle("2026-07-21 16:05:00", 101, 30),
            ],
            "2026-07-22": [candle("2026-07-22 04:00:00", 101, 40)],
        }
        result = directional_features(by_date, "2026-07-22")
        self.assertTrue(result["directional_buy_proxy_available"])
        self.assertEqual(result["afterhours_relative_buy_volume_proxy"], 3.0)
        self.assertEqual(result["premarket_relative_buy_volume_proxy"], 4.0)


if __name__ == "__main__":
    unittest.main()
