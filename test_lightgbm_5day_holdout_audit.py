import unittest

from audit_lightgbm_5day_holdout import audit_report, select_validation_threshold


def threshold(value, net, signals):
    return {"threshold": value, "avg_net_return_pct": net, "signal_count": signals}


class LightGBMFiveDayHoldoutAuditTests(unittest.TestCase):
    def test_selects_from_validation_without_test_input(self):
        selected = select_validation_threshold(
            {"thresholds": [threshold(0.5, 1.0, 50), threshold(0.6, 2.0, 40)]}, 30
        )
        self.assertEqual(selected["threshold"], 0.6)

    def test_fails_closed_when_validation_sample_is_too_small(self):
        with self.assertRaisesRegex(ValueError, "minimum signal"):
            select_validation_threshold({"thresholds": [threshold(0.6, 3.0, 29)]}, 30)

    def test_reports_only_the_matching_test_threshold(self):
        report = {
            "target_return_pct": 2.0,
            "round_trip_cost_pct": 0.25,
            "validation_metrics": {"thresholds": [threshold(0.5, 1.0, 50), threshold(0.6, 2.0, 40)]},
            "test_metrics": {"thresholds": [threshold(0.5, 9.0, 100), threshold(0.6, -1.0, 80)]},
        }
        result = audit_report(report, 30)
        self.assertEqual(result["locked_threshold"], 0.6)
        self.assertEqual(result["untouched_test"]["avg_net_return_pct"], -1.0)
        self.assertEqual(result["status"], "RESEARCH_HOLD")


if __name__ == "__main__":
    unittest.main()
