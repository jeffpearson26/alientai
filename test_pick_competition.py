import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from alientai_v2.research.pick_competition import (
    append_submission,
    build_submission,
    competition_manifest,
    load_universe,
    normalize_picks,
)


EASTERN = ZoneInfo("America/New_York")


class PickCompetitionTests(unittest.TestCase):
    def setUp(self):
        self.universe = tuple(f"T{index:03d}" for index in range(101))

    def test_accepts_zero_to_five_picks(self):
        self.assertEqual(normalize_picks([], self.universe), ())
        self.assertEqual(
            normalize_picks(self.universe[:5], self.universe),
            self.universe[:5],
        )

    def test_rejects_too_many_or_outside_universe(self):
        with self.assertRaisesRegex(ValueError, "at most five"):
            normalize_picks(self.universe[:6], self.universe)
        with self.assertRaisesRegex(ValueError, "outside frozen"):
            normalize_picks(["CTXR"], self.universe)

    def test_rejects_duplicate_ticker(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            normalize_picks(["T001", "t001"], self.universe)

    def test_deadline_is_inclusive_but_later_is_rejected(self):
        accepted = build_submission(
            "Jeff", "2026-08-03", ["T001"], self.universe,
            datetime(2026, 8, 3, 9, 25, tzinfo=EASTERN), "round_1",
        )
        self.assertEqual(accepted["picks"], ["T001"])
        with self.assertRaisesRegex(ValueError, "after"):
            build_submission(
                "Jeff", "2026-08-03", ["T001"], self.universe,
                datetime(2026, 8, 3, 9, 25, 1, tzinfo=EASTERN), "round_1",
            )

    def test_abstention_is_explicit(self):
        row = build_submission(
            "Codex", "2026-08-03", [], self.universe,
            datetime(2026, 8, 3, 8, 0, tzinfo=EASTERN), "round_1",
        )
        self.assertTrue(row["abstained"])
        self.assertEqual(row["pick_count"], 0)
        self.assertEqual(row["execution_decision"], "AVOID")

    def test_submission_is_immutable_per_participant_date(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.jsonl"
            row = build_submission(
                "Jeff", "2026-08-03", ["T001"], self.universe,
                datetime(2026, 8, 3, 8, 0, tzinfo=EASTERN), "round_1",
            )
            append_submission(path, row)
            with self.assertRaisesRegex(ValueError, "already has"):
                append_submission(path, row)
            self.assertEqual(len(path.read_text().splitlines()), 1)

    def test_manifest_fingerprints_exact_101_universe(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "symbols.txt"
            path.write_text("\n".join(self.universe) + "\n", encoding="utf-8")
            self.assertEqual(load_universe(path), self.universe)
            manifest = competition_manifest(path)
            self.assertEqual(manifest["universe_size"], 101)
            self.assertEqual(manifest["horizons"], ["20m", "60m", "2d", "5d", "10d", "20d"])
            self.assertFalse(manifest["execution_enabled"])


if __name__ == "__main__":
    unittest.main()

