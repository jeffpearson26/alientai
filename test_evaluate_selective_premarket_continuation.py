import unittest

from evaluate_selective_premarket_continuation import evaluate, metrics


class PremarketContinuationTests(unittest.TestCase):
    def test_thresholds_select_only_qualifying_positive_gaps(self):
        rows = [
            {"premarket_available": True, "premarket_gap_pct": 2.5, "net_return_pct": 6.0},
            {"premarket_available": True, "premarket_gap_pct": 0.5, "net_return_pct": -1.0},
            {"premarket_available": False, "premarket_gap_pct": 8.0, "net_return_pct": 20.0},
        ]
        result = evaluate(rows)
        self.assertEqual(result["all_available"]["rows"], 2)
        self.assertEqual(result["positive_gap_thresholds"]["at_least_2pct"]["rows"], 1)
        self.assertEqual(result["positive_gap_thresholds"]["at_least_3pct"]["rows"], 0)

    def test_metrics_report_continuation_and_tail_rates(self):
        result = metrics([
            {"net_return_pct": 6.0},
            {"net_return_pct": 1.0},
            {"net_return_pct": -5.0},
        ])
        self.assertAlmostEqual(result["win_rate_pct"], 200.0 / 3.0)
        self.assertAlmostEqual(result["large_gain_5pct_rate_pct"], 100.0 / 3.0)
        self.assertAlmostEqual(result["large_loss_5pct_rate_pct"], 100.0 / 3.0)


if __name__ == "__main__":
    unittest.main()
