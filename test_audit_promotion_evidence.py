import unittest

from audit_promotion_evidence import audit


def report(gate="RESEARCH_PASS", with_artifacts=True):
    artifacts = {"base_rows_sha256": "a", "option_features_sha256": "b", "technical_model_sha256": "c"} if with_artifacts else {}
    metrics = {
        "signals": 30, "mean_net_return_pct": 1, "median_net_return_pct": 1,
        "win_rate_after_cost": .6, "fifth_percentile_net_return_pct": -5,
        "worst_trade_net_return_pct": -8, "approximate_cohort_max_drawdown_pct": -9,
        "largest_symbol_signal_share": .1,
    }
    return {"input_artifacts": artifacts, "results": [{"rare_signal_gate": {"status": gate}, **metrics}]}


class PromotionEvidenceTests(unittest.TestCase):
    def test_passing_historical_evidence_is_still_not_authorization(self):
        result = audit(report())
        self.assertTrue(result["candidates"][0]["eligible_for_paper_review"])
        self.assertFalse(result["promotion_authorized"])

    def test_missing_artifact_identity_fails_closed(self):
        result = audit(report(with_artifacts=False))
        self.assertFalse(result["candidates"][0]["eligible_for_paper_review"])
        self.assertEqual(3, len(result["missing_artifact_identities"]))

    def test_historical_hold_is_ineligible(self):
        self.assertFalse(audit(report(gate="RESEARCH_HOLD"))["candidates"][0]["eligible_for_paper_review"])


if __name__ == "__main__":
    unittest.main()
