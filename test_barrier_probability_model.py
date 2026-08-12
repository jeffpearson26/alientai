from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from build_barrier_probability_panel import source_map

from alientai_v2.research.barrier_probability_model import (
    FEATURE_LOOKBACK,
    FEATURE_NAMES,
    adjusted_daily_candles,
    chronological_date_sets,
    project_probability_bounds,
    resolve_barrier,
    technical_features,
)


def candles(count: int, *, high: float = 100.4, low: float = 99.6):
    start = date(2026, 1, 1)
    return [
        {
            "market_date": (start + timedelta(days=index)).isoformat(),
            "open": 100.0,
            "high": high,
            "low": low,
            "close": 100.0,
            "volume": 1_000_000.0,
        }
        for index in range(count)
    ]


class BarrierLabelTests(unittest.TestCase):
    def test_definite_upper_first(self):
        rows = candles(11)
        rows[1]["high"] = 101.6
        result = resolve_barrier(
            rows,
            0,
            upper_pct=0.015,
            lower_pct=0.005,
            horizon_sessions=10,
        )
        self.assertEqual(result["outcome_status"], "definite_upper_first")
        self.assertEqual(result["label_lower_bound"], 1)
        self.assertEqual(result["label_upper_bound"], 1)

    def test_definite_lower_first(self):
        rows = candles(11)
        rows[1]["low"] = 99.4
        result = resolve_barrier(
            rows,
            0,
            upper_pct=0.015,
            lower_pct=0.005,
            horizon_sessions=10,
        )
        self.assertEqual(result["outcome_status"], "definite_lower_first")
        self.assertEqual(result["label_lower_bound"], 0)
        self.assertEqual(result["label_upper_bound"], 0)

    def test_double_touch_becomes_probability_interval(self):
        rows = candles(11)
        rows[1]["high"] = 101.6
        rows[1]["low"] = 99.4
        result = resolve_barrier(
            rows,
            0,
            upper_pct=0.015,
            lower_pct=0.005,
            horizon_sessions=10,
        )
        self.assertEqual(result["outcome_status"], "ambiguous_same_session")
        self.assertEqual(result["label_lower_bound"], 0)
        self.assertEqual(result["label_upper_bound"], 1)
        self.assertIsNone(result["label_conditional_unambiguous"])

    def test_complete_timeout_is_failure(self):
        result = resolve_barrier(
            candles(11),
            0,
            upper_pct=0.015,
            lower_pct=0.005,
            horizon_sessions=10,
        )
        self.assertEqual(result["outcome_status"], "timeout_failure")
        self.assertEqual(result["label_lower_bound"], 0)
        self.assertEqual(result["label_upper_bound"], 0)

    def test_partial_timeout_is_not_mislabeled(self):
        result = resolve_barrier(
            candles(6),
            0,
            upper_pct=0.015,
            lower_pct=0.005,
            horizon_sessions=10,
        )
        self.assertEqual(result["outcome_status"], "incomplete_unresolved")
        self.assertNotIn("label_lower_bound", result)


class BarrierFeatureTests(unittest.TestCase):
    def test_feature_contract_is_finite(self):
        rows = []
        start = date(2025, 1, 1)
        for index in range(FEATURE_LOOKBACK):
            close = 100.0 + index * 0.2 + (index % 5) * 0.03
            rows.append(
                {
                    "market_date": (
                        start + timedelta(days=index)
                    ).isoformat(),
                    "open": close - 0.1,
                    "high": close + 0.6,
                    "low": close - 0.5,
                    "close": close,
                    "volume": 1_000_000.0 + index * 1000,
                }
            )
        features = technical_features(rows)
        self.assertEqual(tuple(features), FEATURE_NAMES)
        self.assertTrue(all(np.isfinite(value) for value in features.values()))

    def test_feature_envelope_tolerates_adjustment_roundoff(self):
        rows = []
        start = date(2025, 1, 1)
        for index in range(FEATURE_LOOKBACK):
            close = 50.0 + index * 0.05
            rows.append(
                {
                    "market_date": (
                        start + timedelta(days=index)
                    ).isoformat(),
                    "open": close,
                    "high": close + 0.2,
                    "low": close - 0.2,
                    "close": close,
                    "volume": 1_000_000.0,
                }
            )
        rows[-1]["low"] = rows[-1]["close"] + 1e-14
        features = technical_features(rows)
        self.assertEqual(tuple(features), FEATURE_NAMES)

    def test_adjustment_uses_same_row_factor_and_raw_volume(self):
        payload = {
            "Meta Data": {"2. Symbol": "XYZ"},
            "Time Series (Daily)": {
                "2026-01-02": {
                    "1. open": "100",
                    "2. high": "110",
                    "3. low": "90",
                    "4. close": "100",
                    "5. adjusted close": "50",
                    "6. volume": "1234",
                    "7. dividend amount": "0",
                    "8. split coefficient": "2",
                }
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "XYZ_daily.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            row = adjusted_daily_candles(path, "XYZ")[0]
        self.assertEqual(row["open"], 50.0)
        self.assertEqual(row["high"], 55.0)
        self.assertEqual(row["low"], 45.0)
        self.assertEqual(row["close"], 50.0)
        self.assertEqual(row["volume"], 1234.0)


class BarrierChronologyTests(unittest.TestCase):
    def test_stage_dates_are_disjoint_and_ordered(self):
        dates = [
            (date(2020, 1, 1) + timedelta(days=index)).isoformat()
            for index in range(1000)
        ]
        stages = chronological_date_sets(dates, embargo_sessions=10)
        named = (
            "train",
            "fit_validation",
            "calibration",
            "policy_validation",
            "sealed_test",
        )
        for left, right in zip(named, named[1:]):
            self.assertLess(max(stages[left]), min(stages[right]))
            self.assertTrue(stages[left].isdisjoint(stages[right]))
        self.assertTrue(stages["embargo"])

    def test_probability_projection_prevents_crossing(self):
        lower, upper, crossed = project_probability_bounds(
            np.asarray([0.2, 0.8]),
            np.asarray([0.4, 0.6]),
        )
        np.testing.assert_allclose(lower, [0.2, 0.6])
        np.testing.assert_allclose(upper, [0.4, 0.8])
        np.testing.assert_array_equal(crossed, [False, True])


class BarrierSourceRoutingTests(unittest.TestCase):
    def test_single_route_can_cover_frozen_universe(self):
        symbols = ["AAA", "BRK.B"]
        mapping = source_map(
            {
                "source_routes": [
                    {
                        "root": "D:/source",
                        "all_universe_symbols": True,
                    }
                ]
            },
            symbols,
        )
        self.assertEqual(
            mapping["AAA"],
            (Path("D:/source/AAA_daily.json"), "AAA"),
        )
        self.assertEqual(
            mapping["BRK.B"],
            (Path("D:/source/BRK-B_daily.json"), "BRK.B"),
        )

    def test_source_route_preserves_explicit_provider_alias(self):
        mapping = source_map(
            {
                "source_symbol_aliases": {"MMC": "MRSH"},
                "source_routes": [
                    {"root": "D:/source", "all_universe_symbols": True}
                ],
            },
            ["MMC"],
        )
        self.assertEqual(
            mapping["MMC"],
            (Path("D:/source/MMC_daily.json"), "MRSH"),
        )

    def test_source_route_rejects_alias_outside_universe(self):
        with self.assertRaisesRegex(ValueError, "aliases"):
            source_map(
                {
                    "source_symbol_aliases": {"OTHER": "ALIAS"},
                    "source_routes": [
                        {"root": "D:/source", "all_universe_symbols": True}
                    ],
                },
                ["AAA"],
            )


if __name__ == "__main__":
    unittest.main()
