import unittest
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from build_contextual_options_prospective_payload import (
    available_symbols,
    validate_decision,
)


class ContextualOptionsProspectivePayloadTests(unittest.TestCase):
    def test_accepts_after_close_actual_session_and_legacy_stored_date(self):
        result = validate_decision(
            "2026-08-03",
            "2026-08-02",
            "2026-08-03T20:30:00+00:00",
            now_utc=datetime(2026, 8, 3, 21, 0, tzinfo=timezone.utc),
        )
        self.assertEqual("2026-08-03T20:30:00+00:00", result.isoformat())

    def test_accepts_retry_before_next_session_open(self):
        result = validate_decision(
            "2026-08-03",
            "2026-08-02",
            "2026-08-04T12:31:00+00:00",
            now_utc=datetime(2026, 8, 4, 12, 40, tzinfo=timezone.utc),
        )
        self.assertEqual("2026-08-04T12:31:00+00:00", result.isoformat())

    def test_rejects_nonmatching_schwab_storage_date(self):
        with self.assertRaisesRegex(ValueError, "following actual market session"):
            validate_decision(
                "2026-08-03",
                "2026-08-01",
                "2026-08-03T20:30:00+00:00",
                now_utc=datetime(2026, 8, 3, 21, 0, tzinfo=timezone.utc),
            )

    def test_rejects_decision_before_close(self):
        with self.assertRaisesRegex(ValueError, "after the stated session close"):
            validate_decision(
                "2026-08-03",
                "2026-08-02",
                "2026-08-03T19:59:00+00:00",
                now_utc=datetime(2026, 8, 3, 21, 0, tzinfo=timezone.utc),
            )

    def test_manifest_excludes_only_explicitly_unavailable_symbols(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "status": "complete",
                        "completed": [
                            "AAA|2026-08-04",
                            "BBB|2026-08-04",
                        ],
                        "unavailable": ["CCC|2026-08-04"],
                        "failed": [],
                    }
                ),
                encoding="utf-8",
            )
            available, unavailable = available_symbols(
                ["AAA", "BBB", "CCC"], path, "2026-08-04"
            )
            self.assertEqual(["AAA", "BBB"], available)
            self.assertEqual(["CCC"], unavailable)

    def test_manifest_may_cover_complete_collected_common_subset(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "status": "complete",
                        "completed": ["AAA|2026-08-04"],
                        "unavailable": [],
                        "failed": [],
                    }
                ),
                encoding="utf-8",
            )
            available, unavailable = available_symbols(
                ["AAA", "BBB"], path, "2026-08-04"
            )
            self.assertEqual(["AAA"], available)
            self.assertEqual([], unavailable)


if __name__ == "__main__":
    unittest.main()
