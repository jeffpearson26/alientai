from __future__ import annotations

import unittest

from attach_next_session_close_labels import (
    attach_labels,
    index_schwab_daily,
    next_session_label,
    price_anchored_next_session_label,
    price_anchored_next_session_label_from_index,
    schwab_regular_session_date,
)


CANDLES = [
    {"date": "2026-08-03", "open": 99, "close": 100},
    {"date": "2026-08-04", "open": 102, "close": 103},
    {"date": "2026-08-05", "open": 104, "close": 105},
]


class AttachNextSessionCloseLabelsTests(unittest.TestCase):
    def test_preserves_close_entry_when_requested(self) -> None:
        result = next_session_label(
            {"symbol": "AAA", "market_date": "2026-08-03"},
            CANDLES,
            entry_assumption="same_session_close",
            round_trip_cost_pct=0.25,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["label_entry_price"], 100.0)
        self.assertEqual(result["label_exit_price"], 103.0)
        self.assertAlmostEqual(result["label_forward_return_1d_pct"], 2.75)

    def test_supports_next_open_to_same_close(self) -> None:
        result = next_session_label(
            {"symbol": "AAA", "market_date": "2026-08-03"},
            CANDLES,
            entry_assumption="next_regular_session_open",
            round_trip_cost_pct=0.25,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["label_entry_market_date"], "2026-08-04")
        self.assertEqual(result["label_entry_price"], 102.0)
        self.assertEqual(result["label_exit_price"], 103.0)

    def test_missing_future_is_unavailable_not_zero(self) -> None:
        result = next_session_label(
            {"symbol": "AAA", "market_date": "2026-08-05"},
            CANDLES,
            entry_assumption="same_session_close",
            round_trip_cost_pct=0.25,
        )
        self.assertIsNone(result)

    def test_attach_reports_missing_symbols(self) -> None:
        rows, unavailable = attach_labels(
            [
                {"symbol": "AAA", "market_date": "2026-08-03"},
                {"symbol": "BBB", "market_date": "2026-08-03"},
            ],
            {"AAA": CANDLES},
            entry_assumption="same_session_close",
            round_trip_cost_pct=0.25,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(unavailable[0]["reason"], "missing_daily_history")

    def test_schwab_timestamp_normalizes_to_us_session_date(self) -> None:
        candle = {
            "date": "2026-08-02",
            "datetime": "2026-08-02T21:00:00",
        }
        self.assertEqual(
            schwab_regular_session_date(candle).isoformat(), "2026-08-03"
        )

    def test_price_anchored_label_uses_next_session_open_to_close(self) -> None:
        candles = [
            {
                "date": "2026-08-02",
                "datetime": "2026-08-02T21:00:00",
                "open": 99,
                "close": 100,
            },
            {
                "date": "2026-08-03",
                "datetime": "2026-08-03T22:00:00",
                "open": 102,
                "close": 103,
            },
        ]
        result = price_anchored_next_session_label(
            {"symbol": "AAA", "market_date": "2026-08-03", "close": 100},
            candles,
            round_trip_cost_pct=0.25,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["label_entry_market_date"], "2026-08-04")
        self.assertEqual(result["label_entry_price"], 102.0)
        self.assertEqual(result["label_exit_price"], 103.0)
        self.assertAlmostEqual(
            result["label_forward_return_1d_pct"],
            (103.0 / 102.0 - 1.0) * 100.0 - 0.25,
        )

    def test_price_anchored_label_fails_closed_on_close_mismatch(self) -> None:
        candles = [
            {
                "date": "2026-08-02",
                "datetime": "2026-08-02T21:00:00",
                "open": 99,
                "close": 100,
            },
            {
                "date": "2026-08-03",
                "datetime": "2026-08-03T22:00:00",
                "open": 102,
                "close": 103,
            },
        ]
        result = price_anchored_next_session_label(
            {"symbol": "AAA", "market_date": "2026-08-03", "close": 99},
            candles,
            round_trip_cost_pct=0.25,
        )
        self.assertIsNone(result)

    def test_price_anchor_handles_unshifted_historical_source_key(self) -> None:
        candles = [
            {
                "date": "2022-10-06",
                "datetime": "2022-10-06T22:00:00",
                "open": 130,
                "close": 127.44,
            },
            {
                "date": "2022-10-09",
                "datetime": "2022-10-09T22:00:00",
                "open": 126,
                "close": 125,
            },
        ]
        result = price_anchored_next_session_label(
            {
                "symbol": "AAA",
                "market_date": "2022-10-06",
                "close": 127.44,
            },
            candles,
            round_trip_cost_pct=0.25,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["decision_daily_source_date"], "2022-10-06")
        self.assertEqual(result["daily_source_date"], "2022-10-09")
        self.assertEqual(result["label_entry_market_date"], "2022-10-10")

    def test_indexed_and_wrapper_labels_match(self) -> None:
        candles = [
            {
                "date": "2026-08-02",
                "datetime": "2026-08-02T21:00:00",
                "open": 99,
                "close": 100,
            },
            {
                "date": "2026-08-03",
                "datetime": "2026-08-03T22:00:00",
                "open": 102,
                "close": 103,
            },
        ]
        row = {
            "symbol": "AAA",
            "market_date": "2026-08-03",
            "close": 100,
        }
        wrapped = price_anchored_next_session_label(
            row, candles, round_trip_cost_pct=0.25
        )
        indexed = price_anchored_next_session_label_from_index(
            row, index_schwab_daily(candles), round_trip_cost_pct=0.25
        )
        self.assertEqual(indexed, wrapped)


if __name__ == "__main__":
    unittest.main()
