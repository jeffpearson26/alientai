from __future__ import annotations

import unittest

from alientai_v2.research.selective_premarket_features import (
    join_natural_premarket_features,
)


def base(symbol="AAA"):
    return {"symbol": symbol, "market_date": "2026-07-24", "technical_rsi_14": 50.0}


def premarket(symbol="AAA", **overrides):
    row = {
        "symbol": symbol,
        "market_date": "2026-07-24",
        "premarket_available": True,
        "premarket_cutoff_et": "09:25",
        "premarket_last_timestamp_et": "2026-07-24 09:25:00",
        "premarket_gap_pct": 2.0,
        "premarket_relative_volume": 3.0,
    }
    row.update(overrides)
    return row


class SelectivePremarketFeatureTests(unittest.TestCase):
    def test_exact_natural_join_adds_premarket_fields(self):
        rows = join_natural_premarket_features([base()], [premarket()])
        self.assertEqual(2.0, rows[0]["premarket_gap_pct"])
        self.assertEqual(50.0, rows[0]["technical_rsi_14"])

    def test_blocks_matched_winner_control_table(self):
        with self.assertRaisesRegex(ValueError, "matched winner/control"):
            join_natural_premarket_features(
                [base()],
                [premarket(study_label=1, study_role="winner")],
            )

    def test_requires_exact_keys(self):
        with self.assertRaisesRegex(ValueError, "match the base panel exactly"):
            join_natural_premarket_features([base("AAA")], [premarket("BBB")])

    def test_rejects_late_or_wrong_cutoff(self):
        with self.assertRaisesRegex(ValueError, "must be 09:25"):
            join_natural_premarket_features(
                [base()],
                [premarket(premarket_cutoff_et="09:30")],
            )
        with self.assertRaisesRegex(ValueError, "exceeds decision cutoff"):
            join_natural_premarket_features(
                [base()],
                [premarket(premarket_last_timestamp_et="2026-07-24 09:26:00")],
            )

    def test_unavailable_rows_preserve_missingness(self):
        rows = join_natural_premarket_features(
            [base()],
            [premarket(
                premarket_available=False,
                premarket_last_timestamp_et=None,
                premarket_gap_pct=None,
            )],
        )
        self.assertFalse(rows[0]["premarket_available"])
        self.assertIsNone(rows[0]["premarket_gap_pct"])


if __name__ == "__main__":
    unittest.main()
