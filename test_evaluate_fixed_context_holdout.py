from __future__ import annotations

import unittest

from evaluate_fixed_context_holdout import partition


class FixedContextHoldoutTests(unittest.TestCase):
    def test_partitions_dates_without_overlap(self) -> None:
        rows = [{"market_date": "2026-01-01"}, {"market_date": "2026-02-01"}, {"market_date": "2026-03-01"}]
        calibration, holdout = partition(rows, "2026-01-31", "2026-03-01")
        self.assertEqual([row["market_date"] for row in calibration], ["2026-01-01"])
        self.assertEqual([row["market_date"] for row in holdout], ["2026-03-01"])

    def test_rejects_overlapping_boundaries(self) -> None:
        with self.assertRaises(ValueError):
            partition([{"market_date": "2026-01-01"}], "2026-01-02", "2026-01-02")


if __name__ == "__main__":
    unittest.main()
