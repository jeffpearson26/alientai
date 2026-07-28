import unittest
from datetime import date

from build_nasdaq100_one_day_labels import TARGET, attach_labels, target_name
from evaluate_nasdaq100_ten_day_portfolio import select_capacity
from evaluate_nasdaq100_one_day_portfolio import metrics, select_daily


class NasdaqOneDayTests(unittest.TestCase):
    def test_label_enters_next_open_and_exits_next_close(self):
        rows = [{"symbol": "AAA", "market_date": "2026-01-02", "close": 100.0}]
        daily = {"AAA": [
            {"date": date(2026, 1, 2), "open": 99.0, "close": 100.0},
            {"date": date(2026, 1, 5), "open": 101.0, "close": 103.02},
        ]}
        labeled, counts = attach_labels(rows, daily)
        self.assertEqual(counts["labeled_rows"], 1)
        self.assertAlmostEqual(labeled[0][TARGET], 2.0)
        self.assertEqual(labeled[0]["label_entry_market_date"], "2026-01-05")

    def test_daily_selection_keeps_five_highest_scores(self):
        rows = [
            {"label_entry_market_date": "2026-01-05", "technical_context_score": index / 10}
            for index in range(10)
        ]
        selected = select_daily(rows, cutoff=0.0, maximum=5)
        self.assertEqual([row["technical_context_score"] for row in selected], [0.9, 0.8, 0.7, 0.6, 0.5])

    def test_idle_slots_remain_cash(self):
        rows = [{
            TARGET: 5.25, "label_entry_market_date": "2026-01-05",
            "technical_context_score": 1.0,
        }]
        result = metrics(rows, cost=0.25, slots=5)
        self.assertAlmostEqual(result["capital_scaled_return_pct"], 1.0)

    def test_ten_session_label_uses_next_open_and_tenth_close(self):
        candles = [
            {"date": date(2026, 1, 2 + index), "open": 100.0, "close": 100.0}
            for index in range(11)
        ]
        candles[10]["close"] = 110.0
        labeled, counts = attach_labels(
            [{"symbol": "AAA", "market_date": "2026-01-02", "close": 100.0}],
            {"AAA": candles}, horizon_sessions=10,
        )
        self.assertEqual(counts["labeled_rows"], 1)
        self.assertAlmostEqual(labeled[0][target_name(10)], 10.0)
        self.assertEqual(labeled[0]["label_entry_market_date"], "2026-01-03")
        self.assertEqual(labeled[0]["label_exit_market_date"], "2026-01-12")

    def test_ten_day_capacity_rejects_overlapping_sixth_trade(self):
        rows = [{
            "symbol": str(index), "label_entry_market_date": "2026-01-05",
            "label_exit_market_date": "2026-01-20",
            "technical_context_score": 1.0 - index / 100,
        } for index in range(6)]
        self.assertEqual(len(select_capacity(rows, cutoff=0.0, slots=5)), 5)


if __name__ == "__main__":
    unittest.main()
