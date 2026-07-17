from __future__ import annotations

import unittest

import numpy as np

from train_v2_transformer_20day_sp500_from_supabase import (
    apply_standardizer,
    chronological_three_way_indices,
    standardize_train_val,
)


DAY_MS = 24 * 60 * 60 * 1000


class TransformerThreeWaySplitTests(unittest.TestCase):
    def test_split_uses_whole_timestamps_and_embargoes(self):
        timestamps = np.repeat(np.arange(100, dtype=np.int64) * DAY_MS, 2)
        train, validation, test, details = chronological_three_way_indices(
            timestamps,
            embargo_calendar_days=2,
        )

        self.assertEqual(120, len(train))
        self.assertEqual(36, len(validation))
        self.assertEqual(36, len(test))
        self.assertLess(timestamps[train].max(), timestamps[validation].min())
        self.assertLess(timestamps[validation].max(), timestamps[test].min())
        self.assertEqual(2, details["embargo_calendar_days"])

    def test_all_rows_for_same_timestamp_stay_together(self):
        timestamps = np.repeat(np.arange(20, dtype=np.int64) * DAY_MS, 5)
        train, validation, test, _ = chronological_three_way_indices(
            timestamps,
            embargo_calendar_days=0,
        )
        partitions = [set(timestamps[index].tolist()) for index in (train, validation, test)]
        self.assertTrue(partitions[0].isdisjoint(partitions[1]))
        self.assertTrue(partitions[1].isdisjoint(partitions[2]))
        self.assertTrue(partitions[0].isdisjoint(partitions[2]))

    def test_scaler_is_fit_only_on_training_data(self):
        x_train = np.array([[[1.0]], [[3.0]]], dtype=np.float32)
        x_validation = np.array([[[101.0]]], dtype=np.float32)
        x_test = np.array([[[201.0]]], dtype=np.float32)

        train_scaled, _, scaler = standardize_train_val(x_train, x_validation)
        test_scaled = apply_standardizer(x_test, scaler)

        self.assertAlmostEqual(0.0, float(train_scaled.mean()), places=6)
        self.assertEqual([2.0], scaler["mean"])
        self.assertGreater(float(test_scaled[0, 0, 0]), 100.0)

    def test_invalid_fractions_fail_closed(self):
        timestamps = np.arange(20, dtype=np.int64) * DAY_MS
        with self.assertRaises(ValueError):
            chronological_three_way_indices(
                timestamps,
                train_fraction=0.8,
                validation_fraction=0.2,
            )


if __name__ == "__main__":
    unittest.main()
