import unittest

import numpy as np

from train_ai_semiconductor_multi_horizon_catalyst import (
    choose_fraction,
    select_daily,
    trade_metrics,
)


class MultiHorizonTrainerTests(unittest.TestCase):
    def test_daily_selection_does_not_mix_dates(self):
        rows = [
            {"market_date": "2026-01-02", "symbol": "A", "target": 1.0},
            {"market_date": "2026-01-02", "symbol": "B", "target": 2.0},
            {"market_date": "2026-01-03", "symbol": "A", "target": 3.0},
            {"market_date": "2026-01-03", "symbol": "B", "target": 4.0},
        ]
        selected = select_daily(rows, np.asarray([0.1, 0.9, 0.8, 0.2]), "target", 0.5)
        self.assertEqual(selected, [2.0, 3.0])

    def test_fraction_is_selected_on_validation_mean(self):
        metrics = {
            "0.1": {"count": 20, "mean_net_return_pct": 1.0, "positive_rate": 0.5},
            "0.2": {"count": 40, "mean_net_return_pct": 2.0, "positive_rate": 0.4},
            "0.3": {"count": 60, "mean_net_return_pct": 0.0, "positive_rate": 0.7},
        }
        self.assertEqual(choose_fraction(metrics), 0.2)

    def test_metrics_are_cost_adjusted_input_agnostic(self):
        result = trade_metrics([-1.0, 1.0, 5.0], threshold=5.0)
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["positive_rate"], 0.666667)
        self.assertEqual(result["large_move_rate"], 0.333333)


if __name__ == "__main__":
    unittest.main()
