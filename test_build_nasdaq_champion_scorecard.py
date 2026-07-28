import unittest

from build_nasdaq_champion_scorecard import replacement_gate


class NasdaqChampionScorecardTests(unittest.TestCase):
    @staticmethod
    def candidate():
        return {
            "complete_current_universe": True,
            "validation": {
                "signals": 20, "mean_net_return_pct": 1,
                "median_net_return_pct": 1, "net_win_rate_pct": 55,
            },
            "confirmation": {
                "signals": 30, "mean_net_return_pct": 1,
                "median_net_return_pct": 1, "net_win_rate_pct": 60,
                "capital_scaled_max_drawdown_pct": -10,
            },
            "prospective": {"completed_signals": 30},
        }

    def test_complete_evidence_can_pass(self):
        self.assertEqual(
            replacement_gate(self.candidate())["status"], "REPLACEMENT_ELIGIBLE"
        )

    def test_missing_prospective_evidence_fails(self):
        candidate = self.candidate()
        candidate["prospective"]["completed_signals"] = 0
        gate = replacement_gate(candidate)
        self.assertEqual(gate["status"], "NOT_REPLACEMENT_ELIGIBLE")
        self.assertIn("prospective_minimum_30", gate["failed_checks"])

    def test_confirmation_sample_cannot_be_replaced_by_high_return(self):
        candidate = self.candidate()
        candidate["confirmation"]["signals"] = 3
        candidate["confirmation"]["mean_net_return_pct"] = 100
        self.assertEqual(
            replacement_gate(candidate)["status"], "NOT_REPLACEMENT_ELIGIBLE"
        )


if __name__ == "__main__":
    unittest.main()
