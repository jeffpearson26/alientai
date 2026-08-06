from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from alientai_v2.research.multiresolution_cross_sectional import (
    add_cross_sectional_ranks,
    add_option_history_features,
    five_minute_session_features,
    purged_date_folds,
)


class MultiresolutionCrossSectionalTests(unittest.TestCase):
    def test_cross_sectional_ranks_are_date_local(self) -> None:
        frame = pd.DataFrame(
            {
                "market_date": ["2026-01-02"] * 3 + ["2026-01-05"] * 2,
                "symbol": ["A", "B", "C", "A", "B"],
                "signal": [10.0, 20.0, 30.0, 100.0, 0.0],
            }
        )
        ranked = add_cross_sectional_ranks(frame, ["signal"])
        self.assertEqual(
            ranked["rank_signal"].round(3).tolist(),
            [0.0, 0.5, 1.0, 1.0, 0.0],
        )

    def test_option_history_uses_strictly_prior_rows(self) -> None:
        frame = pd.DataFrame(
            {
                "symbol": ["A"] * 11,
                "market_date": pd.date_range(
                    "2026-01-01", periods=11, freq="D"
                ).strftime("%Y-%m-%d"),
                "call_volume": [10.0] * 10 + [20.0],
                "call_open_interest": [100.0] * 11,
            }
        )
        output = add_option_history_features(frame)
        self.assertTrue(
            np.isnan(output.iloc[9]["call_volume_prior10_median_ratio"])
        )
        self.assertEqual(
            output.iloc[10]["call_volume_prior10_median_ratio"], 2.0
        )

    def test_complete_five_minute_session(self) -> None:
        regular = pd.date_range(
            "2026-01-05 09:30", "2026-01-05 15:55", freq="5min"
        )
        after = pd.date_range(
            "2026-01-05 16:00", "2026-01-05 19:55", freq="5min"
        )
        times = regular.append(after)
        close = np.linspace(100.0, 102.0, len(times))
        frame = pd.DataFrame(
            {
                "timestamp": times,
                "open": close - 0.02,
                "high": close + 0.05,
                "low": close - 0.05,
                "close": close,
                "volume": 100.0,
            }
        )
        features = five_minute_session_features(
            frame, source_interval_minutes=5
        )
        self.assertIsNotNone(features)
        assert features is not None
        self.assertGreater(features["afterhours_return_pct"], 0.0)
        self.assertEqual(len(features), 13)

    def test_incomplete_afterhours_fails_closed(self) -> None:
        times = pd.date_range(
            "2026-01-05 09:30", "2026-01-05 15:55", freq="5min"
        )
        frame = pd.DataFrame(
            {
                "timestamp": times,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 100.0,
            }
        )
        self.assertIsNone(
            five_minute_session_features(frame, source_interval_minutes=5)
        )

    def test_purged_folds_exclude_overlap_and_embargo(self) -> None:
        dates = pd.bdate_range("2026-01-02", periods=45)
        rows = pd.DataFrame(
            {
                "market_date": dates.strftime("%Y-%m-%d"),
                "label_entry_date": (
                    dates + pd.offsets.BDay(1)
                ).strftime("%Y-%m-%d"),
                "label_exit_date": (
                    dates + pd.offsets.BDay(5)
                ).strftime("%Y-%m-%d"),
            }
        )
        folds = purged_date_folds(rows, horizon_sessions=5, n_splits=3)
        self.assertEqual(len(folds), 3)
        for fold in folds:
            self.assertFalse(
                set(fold.train_dates) & set(fold.validation_dates)
            )
            self.assertFalse(set(fold.train_dates) & set(fold.embargo_dates))
            validation = rows[
                rows["market_date"].isin(fold.validation_dates)
            ]
            start = validation["market_date"].min()
            end = validation["label_exit_date"].max()
            training = rows[rows["market_date"].isin(fold.train_dates)]
            overlap = (
                (training["label_entry_date"] <= end)
                & (training["label_exit_date"] >= start)
            )
            self.assertFalse(overlap.any())


if __name__ == "__main__":
    unittest.main()
