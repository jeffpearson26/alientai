import unittest
from datetime import date, timedelta

from evaluate_nasdaq_correlation_control import (
    choose_threshold,
    correlation_limited,
    trailing_correlation,
)


class NasdaqCorrelationControlTests(unittest.TestCase):
    @staticmethod
    def path(multiplier=1.0, inverse=False):
        start = date(2025, 1, 1)
        values = {}
        price = 100.0
        for index in range(80):
            move = (1 if index % 2 else -1) * multiplier
            if inverse:
                move *= -1
            price += move
            values[start + timedelta(days=index)] = price
        return values

    def test_trailing_correlation_detects_similar_paths(self):
        day = date(2025, 3, 21)
        self.assertGreater(trailing_correlation(
            self.path(), self.path(2.0), day, minimum_common=40
        ), 0.99)
        self.assertLess(trailing_correlation(
            self.path(), self.path(inverse=True), day, minimum_common=40
        ), -0.99)

    def test_control_rejects_highly_correlated_open_position(self):
        rows = [
            {
                "symbol": "AAA", "market_date": "2025-03-15",
                "future_market_date": "2025-03-20", "technical_context_score": 0.9,
            },
            {
                "symbol": "BBB", "market_date": "2025-03-15",
                "future_market_date": "2025-03-20", "technical_context_score": 0.8,
            },
        ]
        selected, rejected = correlation_limited(
            rows, {"AAA": self.path(), "BBB": self.path(2.0)}, 5, 0.75
        )
        self.assertEqual([row["symbol"] for row in selected], ["AAA"])
        self.assertEqual(rejected["rejected_for_correlation"], 1)

    def test_threshold_choice_uses_return_to_drawdown(self):
        common = {
            "signals": 20, "mean_net_return_pct": 1.0,
            "median_net_return_pct": 1.0, "net_win_rate_pct": 55.0,
        }
        winner = choose_threshold([
            {**common, "maximum_correlation": 0.6,
             "capital_scaled_final_return_pct": 10.0,
             "capital_scaled_max_drawdown_pct": -5.0},
            {**common, "maximum_correlation": 0.9,
             "capital_scaled_final_return_pct": 12.0,
             "capital_scaled_max_drawdown_pct": -12.0},
        ], 20)
        self.assertEqual(winner["maximum_correlation"], 0.6)


if __name__ == "__main__":
    unittest.main()
