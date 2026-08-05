from __future__ import annotations

import json
import unittest
from pathlib import Path

from validate_next_session_close_clone_registry import validate_registry


REGISTRY = Path(__file__).with_name("next_session_close_clone_registry.json")


class NextSessionCloneRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_current_registry_passes(self) -> None:
        result = validate_registry(self.payload)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["clone_count"], 6)

    def test_execution_cannot_be_enabled(self) -> None:
        self.payload["execution_enabled"] = True
        with self.assertRaisesRegex(ValueError, "execution"):
            validate_registry(self.payload)

    def test_horizon_cannot_drift(self) -> None:
        self.payload["clones"][0]["target_horizon_sessions"] = 5
        with self.assertRaisesRegex(ValueError, "one complete session"):
            validate_registry(self.payload)

    def test_source_model_set_is_immutable(self) -> None:
        self.payload["clones"][0]["source_model_id"] = "unknown"
        with self.assertRaisesRegex(ValueError, "source-model set"):
            validate_registry(self.payload)


if __name__ == "__main__":
    unittest.main()
