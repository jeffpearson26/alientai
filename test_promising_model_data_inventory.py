from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from update_promising_model_data_inventory import (
    audit_requirement,
    audit_jsonl,
    audit_manifest,
    build_inventory,
)


class PromisingModelDataInventoryTests(unittest.TestCase):
    def test_manifest_can_require_completed_plus_unavailable_accounting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "status": "complete",
                        "completed": [{"request": "AAA|2026-07"}],
                        "unavailable": [{"request": "OLD|2020-01"}],
                        "failed": [],
                    }
                ),
                encoding="utf-8",
            )
            result = audit_manifest(path, {"required_accounted": 2})
            self.assertEqual(result["state"], "READY")
            self.assertEqual(result["accounted"], 2)

    def test_manifest_reason_omits_zero_completed_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "status": "running",
                        "completed": [{"request": "AAA|2020-01"}],
                        "unavailable": [],
                        "failed": [],
                    }
                ),
                encoding="utf-8",
            )
            result = audit_manifest(path, {"required_accounted": 8137})
            self.assertEqual(result["state"], "BLOCKED")
            self.assertIn("8137 accounted required", result["reason"])
            self.assertNotIn("0 completed", result["reason"])

    def test_boolean_coverage_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "panel.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "symbol": "AAA",
                                "market_date": "2026-08-04",
                                "available": True,
                            }
                        ),
                        json.dumps(
                            {
                                "symbol": "BBB",
                                "market_date": "2026-08-04",
                                "available": False,
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            result = audit_jsonl(
                path,
                {
                    "required_rows": 2,
                    "date_field": "market_date",
                    "boolean_field": "available",
                },
                datetime(2026, 8, 4, 15, tzinfo=timezone.utc),
            )
            self.assertEqual(result["state"], "BLOCKED")
            self.assertEqual(result["usable_rows"], 1)

    def test_model_is_blocked_when_dependency_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = {
                "requirements": {
                    "missing": {
                        "kind": "file",
                        "path": "does-not-exist.json",
                        "data_type": "test",
                        "source": "test",
                        "timing_contract": "test",
                    }
                },
                "models": [
                    {
                        "model_id": "example",
                        "display_name": "Example",
                        "requirements": ["missing"],
                    }
                ],
            }
            result = build_inventory(Path(directory), registry)
            self.assertEqual(result["models"][0]["state"], "BLOCKED")
            self.assertEqual(result["models"][0]["blocked_requirements"], ["missing"])

    def test_json_status_requires_exact_ready_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "readiness.json"
            path.write_text(
                json.dumps({"status": "BLOCKED"}), encoding="utf-8"
            )
            result = audit_requirement(
                root,
                {
                    "kind": "json_status",
                    "path": "readiness.json",
                    "required_status": "READY_TO_BUILD_PANEL",
                },
                datetime(2026, 8, 5, tzinfo=timezone.utc),
            )
            self.assertEqual(result["state"], "BLOCKED")
            self.assertIn("required 'READY_TO_BUILD_PANEL'", result["reason"])


if __name__ == "__main__":
    unittest.main()
