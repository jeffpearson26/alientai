from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from alientai_v2.engines.rcef_evidence import (
    build_event_specialist, build_news_specialist, build_rcef_evidence,
    point_in_time_rows,
)


NOW = datetime(2026, 7, 18, 16, 0, tzinfo=timezone.utc)


def candles(multiplier=1.0):
    start = NOW - timedelta(days=40)
    return [
        {"datetime_utc": (start + timedelta(days=i)).isoformat(), "close": multiplier * (100 + i)}
        for i in range(31)
    ]


class RCEFEvidenceTests(unittest.TestCase):
    def test_future_rows_are_never_visible(self):
        rows = [
            {"published_at": (NOW - timedelta(hours=1)).isoformat(), "id": "past"},
            {"published_at": (NOW + timedelta(hours=1)).isoformat(), "id": "future"},
        ]
        self.assertEqual([row["id"] for row in point_in_time_rows(rows, NOW)], ["past"])

    def test_as_of_is_mandatory(self):
        with self.assertRaises(ValueError):
            build_rcef_evidence({})

    def test_insider_sales_are_ignored(self):
        rows = [
            {"filed_at": (NOW - timedelta(days=1)).isoformat(), "event_type": "insider_sale", "value": 9_000_000},
        ]
        result = build_event_specialist(rows, NOW)
        self.assertFalse(result["available"])

    def test_large_open_market_purchase_is_positive(self):
        rows = [
            {"filed_at": (NOW - timedelta(days=1)).isoformat(), "event_type": "open_market_purchase", "value": 2_000_000},
        ]
        result = build_event_specialist(rows, NOW)
        self.assertTrue(result["available"])
        self.assertGreater(result["expected_excess_return_pct"], 0)

    def test_hold_to_buy_upgrade_is_positive(self):
        rows = [{
            "announced_at": (NOW - timedelta(days=2)).isoformat(), "event_type": "rating_upgrade",
            "from_rating": "Hold", "to_rating": "Buy",
        }]
        result = build_event_specialist(rows, NOW)
        self.assertGreater(result["expected_excess_return_pct"], 1.0)

    def test_future_news_cannot_change_score(self):
        past = {"published_at": (NOW - timedelta(hours=1)).isoformat(), "sentiment": 0.4, "ticker_relevance_score": 1}
        future = {"published_at": (NOW + timedelta(hours=1)).isoformat(), "sentiment": -1, "ticker_relevance_score": 1}
        first = build_news_specialist([past], NOW)
        second = build_news_specialist([past, future], NOW)
        self.assertEqual(first["expected_excess_return_pct"], second["expected_excess_return_pct"])

    def test_missing_optional_sources_reduce_data_quality(self):
        result = build_rcef_evidence({
            "as_of": NOW, "candles": candles(1.02), "benchmark_candles": candles(),
            "market_context": {"spy_return_20d_pct": 2, "breadth_above_50d_pct": 55},
            "analogs": {"cases": 50}, "liquidity_score": 0.9,
        })
        self.assertEqual(result["data_quality"], 0.5)
        self.assertFalse(result["specialists"]["events"]["available"])
        self.assertFalse(result["specialists"]["news"]["available"])


if __name__ == "__main__":
    unittest.main()
