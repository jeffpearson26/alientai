from __future__ import annotations

import unittest

from alientai_v2.research.five_day_open_close_labels import (
    build_next_open_horizon_close_labels,
    build_next_open_five_close_labels,
)


def candles():
    return [
        {"date": "2026-07-13", "open": 99.0, "close": 100.0},
        {"date": "2026-07-14", "open": 100.0, "close": 101.0},
        {"date": "2026-07-15", "open": 101.0, "close": 102.0},
        {"date": "2026-07-16", "open": 102.0, "close": 103.0},
        {"date": "2026-07-17", "open": 103.0, "close": 104.0},
        {"date": "2026-07-20", "open": 104.0, "close": 105.0},
        {"date": "2026-07-21", "open": 105.0, "close": 106.0},
    ]


class FiveDayOpenCloseLabelTests(unittest.TestCase):
    def test_generic_two_session_horizon_uses_second_close(self):
        rows = candles()
        labels = build_next_open_horizon_close_labels(
            "AAA", rows, horizon_sessions=2, round_trip_cost_pct=0.0
        )
        first = labels[0]
        self.assertEqual(first["holding_sessions"], 2)
        self.assertEqual(first["entry_date"], rows[1]["date"])
        self.assertEqual(first["exit_date"], rows[2]["date"])
        self.assertEqual(first["exit_price"], rows[2]["close"])

    def test_uses_next_open_and_fifth_session_close(self):
        rows = build_next_open_five_close_labels("abc", candles())
        first = rows[0]
        self.assertEqual("ABC", first["symbol"])
        self.assertEqual("2026-07-13", first["decision_date"])
        self.assertEqual("2026-07-14", first["entry_date"])
        self.assertEqual("2026-07-20", first["exit_date"])
        self.assertEqual(100.0, first["entry_price"])
        self.assertEqual(105.0, first["exit_price"])
        self.assertAlmostEqual(4.75, first["net_return_pct"])
        self.assertEqual(1, first["label_large_move"])

    def test_does_not_emit_label_without_complete_future(self):
        rows = build_next_open_five_close_labels("ABC", candles()[:5])
        self.assertEqual([], rows)

    def test_subtracts_frozen_round_trip_cost(self):
        rows = build_next_open_five_close_labels(
            "ABC",
            candles(),
            round_trip_cost_pct=1.0,
            large_move_target_pct=5.0,
        )
        self.assertAlmostEqual(4.0, rows[0]["net_return_pct"])
        self.assertEqual(1, rows[0]["label_positive_net_return"])
        self.assertEqual(0, rows[0]["label_large_move"])

    def test_skips_discontinuous_window(self):
        source = candles()
        source[3] = {**source[3], "date": "2026-08-16"}
        source[4] = {**source[4], "date": "2026-08-17"}
        source[5] = {**source[5], "date": "2026-08-20"}
        source[6] = {**source[6], "date": "2026-08-21"}
        rows = build_next_open_five_close_labels("ABC", source)
        self.assertEqual([], rows)

    def test_skips_invalid_prices_instead_of_calling_them_losses(self):
        source = candles()
        source[1] = {**source[1], "open": 0.0}
        rows = build_next_open_five_close_labels("ABC", source)
        self.assertEqual(1, len(rows))
        self.assertEqual("2026-07-14", rows[0]["decision_date"])

    def test_rejects_unsorted_or_duplicate_dates(self):
        source = candles()
        source[2] = {**source[2], "date": source[1]["date"]}
        with self.assertRaises(ValueError):
            build_next_open_five_close_labels("ABC", source)


if __name__ == "__main__":
    unittest.main()
