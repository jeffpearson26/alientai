import unittest

from evaluate_contextual_options_prospective_gate import evaluate


def report(records, source="schwab_local_daily_csv"):
    return {"research_only": True, "execution_enabled": False, "source": source, "records": records}


class ContextualOptionsProspectiveGateTests(unittest.TestCase):
    def test_holds_when_no_completed_outcomes_exist(self):
        result = evaluate([report([])])
        self.assertEqual(result["status"], "RESEARCH_HOLD")
        self.assertFalse(result["prospective_paper_review_eligible"])

    def test_rejects_unapproved_source_and_duplicates(self):
        record = {"outcome_status": "COMPLETE", "shadow_policy_id": "p", "symbol": "ABC", "market_date": "2026-01-02", "realized_return_pct": 1.0}
        result = evaluate([report([record, record]), report([record], source="other")])
        self.assertIn("missing_or_duplicate_outcome_identity", result["input_failures"])
        self.assertIn("report_source_not_approved", result["input_failures"])
        self.assertEqual(result["status"], "RESEARCH_HOLD")

    def test_ignores_legacy_progress_snapshot_without_completed_outcomes(self):
        completed = {"outcome_status": "COMPLETE", "shadow_policy_id": "p", "symbol": "ABC", "market_date": "2026-01-02", "realized_return_pct": 1.0}
        legacy_progress = {"research_only": True, "execution_enabled": False, "records": []}
        result = evaluate([legacy_progress, report([completed])])
        self.assertEqual(result["completed_outcomes"], 1)
        self.assertNotIn("report_source_not_approved", result["input_failures"])


if __name__ == "__main__":
    unittest.main()
