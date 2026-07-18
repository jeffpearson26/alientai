from __future__ import annotations

import unittest
from datetime import date, timedelta

from alientai_v2.research.rcef_rows import build_research_rows, market_close_utc


def candles(multiplier=1.0, count=75):
    start = date(2026, 1, 1)
    return [{"date": (start + timedelta(days=i)).isoformat(), "close": multiplier * (100 + i)} for i in range(count)]


class RCEFResearchRowTests(unittest.TestCase):
    def test_market_close_uses_dst_aware_eastern_time(self):
        self.assertEqual(market_close_utc(date(2026, 7, 1)).hour, 20)
        self.assertEqual(market_close_utc(date(2026, 1, 1)).hour, 21)

    def test_five_day_label_uses_strictly_future_close(self):
        rows = build_research_rows(symbol="XYZ", candles=candles(), benchmark_candles=candles())
        first = rows[0]
        self.assertEqual(first["market_date"], "2026-03-01")
        self.assertEqual(first["future_market_date"], "2026-03-06")
        self.assertAlmostEqual(first["label_forward_return_5d_pct"], ((164 / 159) - 1) * 100)

    def test_future_filing_does_not_leak_into_prior_row(self):
        purchase = {
            "ticker": "XYZ", "insider_name": "A", "transaction_code": "P",
            "transaction_date": "2026-03-02", "available_at_utc": "2026-03-04T12:00:00Z",
            "shares": 10, "price": 10, "total_value": 100, "is_training_eligible": True,
        }
        rows = build_research_rows(
            symbol="XYZ", candles=candles(), benchmark_candles=candles(), sec_purchases=[purchase]
        )
        before = next(row for row in rows if row["market_date"] == "2026-03-03")
        after = next(row for row in rows if row["market_date"] == "2026-03-04")
        self.assertFalse(before["insider_purchase_available"])
        self.assertTrue(after["insider_purchase_available"])

    def test_rows_without_full_future_horizon_are_omitted(self):
        rows = build_research_rows(symbol="XYZ", candles=candles(), benchmark_candles=candles())
        self.assertEqual(len(rows), 75 - 60 - 5 + 1)

    def test_future_candles_do_not_change_technical_snapshot(self):
        original = candles(count=75)
        changed_future = candles(count=75)
        changed_future[64]["close"] = 9999
        first = build_research_rows(symbol="XYZ", candles=original, benchmark_candles=original)[0]
        changed = build_research_rows(symbol="XYZ", candles=changed_future, benchmark_candles=original)[0]
        technical_keys = [key for key in first if key.startswith("technical_")]
        self.assertTrue(technical_keys)
        self.assertEqual({key: first[key] for key in technical_keys}, {key: changed[key] for key in technical_keys})


if __name__ == "__main__":
    unittest.main()
