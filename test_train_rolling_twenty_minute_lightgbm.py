from __future__ import annotations

import unittest

import numpy as np

from train_rolling_twenty_minute_lightgbm import (
    Partition,
    max_drawdown_capital_scaled,
    rotating_nonoverlap_mask,
    select_cross_section,
    split_market_dates,
)


class TrainRollingTwentyMinuteTests(unittest.TestCase):
    def test_rotating_sample_is_nonoverlapping_and_changes_phase(self) -> None:
        first = np.arange(
            np.datetime64("2026-07-30T09:30"),
            np.datetime64("2026-07-30T15:40"),
            np.timedelta64(1, "m"),
        ).astype("datetime64[ns]").astype(np.int64)
        second = np.arange(
            np.datetime64("2026-07-31T09:30"),
            np.datetime64("2026-07-31T15:40"),
            np.timedelta64(1, "m"),
        ).astype("datetime64[ns]").astype(np.int64)
        timestamps = np.concatenate([first, second])
        minutes = np.concatenate([np.arange(370), np.arange(370)])
        mask = rotating_nonoverlap_mask(timestamps, minutes)
        selected_minutes = minutes[mask]
        self.assertGreater(len(selected_minutes), 30)
        first_phase = set(selected_minutes[: len(selected_minutes) // 2] % 20)
        second_phase = set(selected_minutes[len(selected_minutes) // 2 :] % 20)
        self.assertEqual(len(first_phase), 1)
        self.assertEqual(len(second_phase), 1)
        self.assertNotEqual(first_phase, second_phase)

    def test_split_is_chronological_with_two_embargoes(self) -> None:
        dates = np.arange(
            np.datetime64("2025-01-01"),
            np.datetime64("2025-07-20"),
            np.timedelta64(1, "D"),
        )
        split = split_market_dates(dates)
        self.assertLess(max(split["train"]), min(split["validation"]))
        self.assertLess(max(split["validation"]), min(split["test"]))
        self.assertTrue(split["embargo"].isdisjoint(split["train"]))
        self.assertTrue(split["embargo"].isdisjoint(split["validation"]))
        self.assertTrue(split["embargo"].isdisjoint(split["test"]))

    def test_cross_section_selection_respects_capacity(self) -> None:
        scores = np.arange(20, dtype=float)
        timestamps = np.array([1] * 10 + [2] * 10)
        selected = select_cross_section(scores, timestamps, 1.0, max_positions=3)
        self.assertEqual(int(selected.sum()), 6)
        self.assertEqual(set(np.flatnonzero(selected)), {7, 8, 9, 17, 18, 19})

    def test_drawdown_scales_unfilled_slots_to_cash(self) -> None:
        partition = Partition(
            x=np.empty((2, 0)),
            net=np.array([-10.0, -10.0]),
            positive=np.zeros(2),
            timestamp=np.array([1, 2]),
            symbol=np.array([0, 0]),
        )
        selected = np.ones(2, dtype=bool)
        drawdown = max_drawdown_capital_scaled(
            partition.net,
            partition.timestamp,
            selected,
            max_positions=5,
        )
        self.assertAlmostEqual(drawdown, -3.96)


if __name__ == "__main__":
    unittest.main()
