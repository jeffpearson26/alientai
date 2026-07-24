import unittest

from audit_alpha_vantage_unavailability_policy import audit


class AlphaVantageUnavailabilityPolicyTests(unittest.TestCase):
    def test_preserves_unavailable_requests_and_classifies_share_classes(self):
        report = audit(
            {"unavailable": ["AAA|2025Q1"]},
            {"unavailable": ["BRK.B|2024-01", "OTHER|2024-02"]},
        )
        self.assertEqual(report["transcripts"]["unavailable_count"], 1)
        self.assertEqual(report["premarket"]["share_class_symbols"], ["BRK.B"])
        self.assertEqual(report["premarket"]["other_symbols"], ["OTHER"])
        self.assertIn("never substitute", report["transcripts"]["join_policy"])


if __name__ == "__main__":
    unittest.main()
