from __future__ import annotations

import unittest

from audit_transformer_artifacts import audit


class TransformerArtifactAuditTests(unittest.TestCase):
    def test_different_build_or_broader_candidate_requires_hold(self) -> None:
        report = audit({"build": "old", "symbols_used": 25}, {"build": "new", "symbols_used": 496})
        self.assertEqual(report["status"], "RESEARCH_HOLD")
        self.assertEqual(len(report["reasons"]), 2)

    def test_matching_artifacts_are_comparable(self) -> None:
        report = audit({"build": "same", "symbols_used": 496}, {"build": "same", "symbols_used": 496})
        self.assertEqual(report["status"], "ARTIFACTS_COMPARABLE")


if __name__ == "__main__":
    unittest.main()
