import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from audit_model_inventory import audit_paths


class ModelInventoryTests(unittest.TestCase):
    def test_flags_pass_without_hashes_and_recognizes_hashed_pass(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "old.json").write_text(json.dumps({"results": [{"rare_signal_gate": {"status": "RESEARCH_PASS"}}]}), encoding="utf-8")
            (root / "new.json").write_text(json.dumps({"input_artifacts": {"technical_model_sha256": "abc"}, "results": [{"rare_signal_gate": {"status": "RESEARCH_PASS"}}]}), encoding="utf-8")
            (root / "hold.json").write_text(json.dumps({"rare_signal_gate": {"status": "RESEARCH_HOLD"}}), encoding="utf-8")
            report = audit_paths(root.glob("*.json"))
        self.assertEqual(3, report["reports_scanned"])
        self.assertEqual(["old.json"], [item["report"] for item in report["nonreproducible_historical_passes"]])
        self.assertEqual(["new.json"], [item["report"] for item in report["reproducible_historical_passes"]])
        self.assertFalse(report["promotion_authorized"])


if __name__ == "__main__":
    unittest.main()
