import json
import tempfile
import unittest
from pathlib import Path

from journal_ai_semiconductor_narrative_model import ensure_manifest, model_entry


class NarrativeJournalTests(unittest.TestCase):
    def test_model_entry_requires_exact_horizon_and_stage(self):
        report = {"models": [
            {"horizon_sessions": 1, "stage": "one"},
            {"horizon_sessions": 5, "stage": "five"},
        ]}
        self.assertEqual(model_entry(report, 1, "one")["stage"], "one")
        with self.assertRaises(ValueError):
            model_entry(report, 1, "five")

    def test_manifest_is_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            ensure_manifest(path, {"status": "frozen", "model_sha256": "a"})
            ensure_manifest(path, {"status": "frozen", "model_sha256": "a"})
            self.assertEqual(json.loads(path.read_text())["model_sha256"], "a")
            with self.assertRaises(ValueError):
                ensure_manifest(path, {"status": "frozen", "model_sha256": "b"})


if __name__ == "__main__":
    unittest.main()
