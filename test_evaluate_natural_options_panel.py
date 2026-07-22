from __future__ import annotations

import unittest

from evaluate_natural_options_panel import daily_top, join_options


class NaturalOptionsPanelTests(unittest.TestCase):
    def test_join_uses_symbol_and_market_date(self):
        result = join_options([{"symbol": "AAA", "market_date": "2026-01-02"}], [{"symbol": "AAA", "market_date": "2026-01-02", "option_call_volume": 10}])
        self.assertEqual(10, result[0]["option_call_volume"])

    def test_daily_top_limits_each_date(self):
        rows = [
            {"symbol": "A", "market_date": "2026-01-02", "future_market_date": "2026-01-09", "raw_score": 0.9},
            {"symbol": "B", "market_date": "2026-01-02", "future_market_date": "2026-01-09", "raw_score": 0.8},
            {"symbol": "C", "market_date": "2026-01-03", "future_market_date": "2026-01-10", "raw_score": 0.7},
        ]
        self.assertEqual(["A", "C"], [row["symbol"] for row in daily_top(rows, 1)])


if __name__ == "__main__":
    unittest.main()
