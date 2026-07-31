import unittest

from summarize_intraday_prospective import summarize


class ProspectiveSummaryTests(unittest.TestCase):
    def test_summary_uses_equal_weight_daily_cohorts(self):
        rows = [
            {"model_id": "m", "market_date": "2026-07-31", "horizon_minutes": 20, "label_forward_return_20m_net_pct": 1.0},
            {"model_id": "m", "market_date": "2026-07-31", "horizon_minutes": 20, "label_forward_return_20m_net_pct": 3.0},
            {"model_id": "m", "market_date": "2026-08-03", "horizon_minutes": 20, "label_forward_return_20m_net_pct": -1.0},
        ]
        model = summarize(rows, minimum_days=3)["models"]["m"]
        self.assertEqual(model["days"], 2)
        self.assertEqual(model["mean_daily_net_return_pct"], 0.5)
        self.assertFalse(model["evidence_gate_met"])

    def test_empty_outcomes_are_valid(self):
        self.assertEqual(summarize([])["models"], {})


if __name__ == "__main__":
    unittest.main()
