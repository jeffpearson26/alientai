from __future__ import annotations

import unittest

from alientai_v2.research.selective_five_day_panel import (
    build_selective_five_day_panel,
)


def feature(symbol: str = "AAA", **overrides):
    result = {
        "symbol": symbol,
        "market_date": "2026-07-13",
        "as_of_utc": "2026-07-13T20:00:00+00:00",
        "decision_cutoff_utc": "2026-07-13T20:05:00+00:00",
        "technical_rsi_14": 55.0,
        "option_available": True,
    }
    result.update(overrides)
    return result


def label(symbol: str = "AAA", **overrides):
    result = {
        "symbol": symbol,
        "decision_date": "2026-07-13",
        "entry_date": "2026-07-14",
        "exit_date": "2026-07-20",
        "entry_price": 100.0,
        "exit_price": 105.0,
        "net_return_pct": 4.75,
        "label_positive_net_return": 1,
        "label_large_move": 1,
    }
    result.update(overrides)
    return result


class SelectiveFiveDayPanelTests(unittest.TestCase):
    def test_exact_join_preserves_feature_and_label_provenance(self):
        rows = build_selective_five_day_panel(
            [feature()],
            [label()],
            required_feature_fields=("technical_rsi_14", "option_available"),
        )
        self.assertEqual(1, len(rows))
        self.assertEqual(55.0, rows[0]["technical_rsi_14"])
        self.assertEqual(4.75, rows[0]["net_return_pct"])
        self.assertEqual("2026-07-13", rows[0]["decision_date"])
        self.assertTrue(rows[0]["research_only"])

    def test_rejects_future_outcomes_on_feature_side(self):
        with self.assertRaisesRegex(ValueError, "forbidden outcome fields"):
            build_selective_five_day_panel(
                [feature(label_forward_return_5d_pct=5.0)],
                [label()],
            )

    def test_rejects_feature_availability_after_decision_cutoff(self):
        with self.assertRaisesRegex(ValueError, "after decision cutoff"):
            build_selective_five_day_panel(
                [feature(as_of_utc="2026-07-13T20:06:00+00:00")],
                [label()],
            )

    def test_requires_exact_keys(self):
        with self.assertRaisesRegex(ValueError, "keys must match exactly"):
            build_selective_five_day_panel([feature("AAA")], [label("BBB")])

    def test_rejects_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError, "duplicate feature key"):
            build_selective_five_day_panel([feature(), feature()], [label()])

    def test_rejects_invalid_label_timing(self):
        with self.assertRaisesRegex(ValueError, "label timing is invalid"):
            build_selective_five_day_panel(
                [feature()],
                [label(entry_date="2026-07-13")],
            )

    def test_requires_timezone_and_required_fields(self):
        with self.assertRaisesRegex(ValueError, "include a timezone"):
            build_selective_five_day_panel(
                [feature(as_of_utc="2026-07-13T20:00:00")],
                [label()],
            )
        with self.assertRaisesRegex(ValueError, "missing required fields"):
            build_selective_five_day_panel(
                [feature()],
                [label()],
                required_feature_fields=("technical_rsi_14", "premarket_gap_pct"),
            )

    def test_rejects_cutoff_on_wrong_date(self):
        with self.assertRaisesRegex(ValueError, "cutoff date does not match"):
            build_selective_five_day_panel(
                [feature(decision_cutoff_utc="2026-07-14T13:25:00+00:00")],
                [label()],
            )


if __name__ == "__main__":
    unittest.main()
