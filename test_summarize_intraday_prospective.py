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

    def test_completed_cohort_rolls_into_next_collecting_cohort(self):
        rows = [
            {
                "model_id": "m", "market_date": f"2026-07-{day:02d}",
                "horizon_minutes": 20, "label_forward_return_20m_net_pct": 1.0,
            }
            for day in range(1, 22)
        ]
        model = summarize(rows, minimum_days=20)["models"]["m"]
        self.assertEqual(model["completed_cohorts"], 1)
        self.assertEqual(model["active_cohort_number"], 2)
        self.assertEqual(model["cohorts"][0]["status"], "complete")
        self.assertEqual(model["cohorts"][1]["status"], "collecting")
        self.assertEqual(model["cohorts"][1]["days"], 1)


if __name__ == "__main__":
    unittest.main()
