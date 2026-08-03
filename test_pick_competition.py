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
    evaluate_pick_outcomes,
    load_universe,
    normalize_picks,
    post_cost_return_pct,
    summarize_returns,
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

    def test_jeff_standing_entry_is_frozen_and_in_universe(self):
        root = Path(__file__).resolve().parent
        contract = json.loads(
            (root / "pick_competition_standing_entries.json").read_text(
                encoding="utf-8"
            )
        )
        entry = contract["standing_entries"][0]
        universe = load_universe(root / "nasdaq100_2026-06_symbols.txt")
        self.assertEqual(entry["participant"], "Jeff")
        self.assertEqual(
            normalize_picks(entry["picks"], universe),
            ("MU", "AVGO", "AMD", "MRVL", "NVDA"),
        )
        self.assertEqual(entry["policy"], "fixed_for_entire_competition")
        self.assertFalse(entry["reselection_allowed"])

    def test_post_cost_return_subtracts_frozen_cost(self):
        self.assertAlmostEqual(post_cost_return_pct(100, 105), 4.75)

    def test_outcomes_remain_pending_until_price_fact_exists(self):
        result = evaluate_pick_outcomes(
            symbol="NVDA",
            entry_price=100,
            entry_at_utc="2026-08-03T13:30:00+00:00",
            horizon_observations={
                "20m": {"as_of_utc": "2026-08-03T13:50:00+00:00", "price": 102},
            },
        )
        self.assertEqual(result["outcomes"]["20m"]["status"], "complete")
        self.assertEqual(result["outcomes"]["60m"]["status"], "pending")
        self.assertAlmostEqual(result["outcomes"]["20m"]["unmanaged_net_return_pct"], 1.75)

    def test_explicit_stop_applies_only_to_later_horizons(self):
        result = evaluate_pick_outcomes(
            symbol="NVDA",
            entry_price=100,
            entry_at_utc="2026-08-03T13:30:00+00:00",
            horizon_observations={
                "20m": {"as_of_utc": "2026-08-03T13:50:00+00:00", "price": 101},
                "60m": {"as_of_utc": "2026-08-03T14:30:00+00:00", "price": 96},
            },
            stop_exit={"as_of_utc": "2026-08-03T14:00:00+00:00", "price": 94},
        )
        self.assertFalse(result["outcomes"]["20m"]["stop_applied"])
        self.assertTrue(result["outcomes"]["60m"]["stop_applied"])
        self.assertAlmostEqual(result["outcomes"]["60m"]["stop_managed_net_return_pct"], -6.25)

    def test_stop_cannot_be_backdated(self):
        with self.assertRaisesRegex(ValueError, "must occur after entry"):
            evaluate_pick_outcomes(
                symbol="NVDA",
                entry_price=100,
                entry_at_utc="2026-08-03T13:30:00+00:00",
                horizon_observations={},
                stop_exit={"as_of_utc": "2026-08-03T13:29:00+00:00", "price": 94},
            )

    def test_summary_reports_honest_sample_statistics(self):
        summary = summarize_returns([2.0, -1.0, 4.0])
        self.assertEqual(summary["sample_size"], 3)
        self.assertAlmostEqual(summary["mean_return_pct"], 5 / 3)
        self.assertEqual(summary["median_return_pct"], 2.0)
        self.assertAlmostEqual(summary["win_rate_pct"], 200 / 3)
        self.assertEqual(summary["worst_return_pct"], -1.0)


if __name__ == "__main__":
    unittest.main()
