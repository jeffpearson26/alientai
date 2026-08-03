from __future__ import annotations

import csv
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from download_alpha_vantage_matched_premarket import archive_path
from evaluate_pick_competition_intraday import (
    append_unique,
    build_outcomes,
    summarize,
)


class PickCompetitionIntradayOutcomeTests(unittest.TestCase):
    def make_archive(self, root: Path, updated: str) -> Path:
        archive = root / "archive"
        archive.mkdir()
        manifest = {
            "status": "complete",
            "mode": "current",
            "entitlement": "realtime",
            "current_date": "2026-08-03",
            "bar_interval_minutes": 5,
            "timestamp_convention": "interval_start",
            "updated_at_utc": updated,
        }
        (archive / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        path = archive_path(archive, "AAA", "2026-08")
        path.parent.mkdir(parents=True)
        with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=("timestamp", "open", "high", "low", "close", "volume"),
            )
            writer.writeheader()
            writer.writerow(
                {
                    "timestamp": "2026-08-03 09:30:00",
                    "open": 100,
                    "high": 102,
                    "low": 99,
                    "close": 101,
                    "volume": 10,
                }
            )
            writer.writerow(
                {
                    "timestamp": "2026-08-03 09:45:00",
                    "open": 101,
                    "high": 103,
                    "low": 100,
                    "close": 102,
                    "volume": 10,
                }
            )
            writer.writerow(
                {
                    "timestamp": "2026-08-03 10:25:00",
                    "open": 102,
                    "high": 104,
                    "low": 101,
                    "close": 103,
                    "volume": 10,
                }
            )
        return archive

    def submission(self) -> dict:
        return {
            "round_id": "r1",
            "participant": "Jeff",
            "decision_date": "2026-08-03",
            "picks": ["AAA"],
        }

    def test_uses_exact_open_and_completed_exit_bar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = self.make_archive(
                Path(directory), "2026-08-03T14:31:00+00:00"
            )
            rows = build_outcomes(
                submissions=[self.submission()],
                archive=archive,
                decision_date="2026-08-03",
                horizon="60m",
            )
        self.assertEqual(rows[0]["entry_price"], 100)
        self.assertEqual(rows[0]["unmanaged_exit_price"], 103)
        self.assertAlmostEqual(rows[0]["unmanaged_net_return_pct"], 2.75)
        self.assertEqual(
            rows[0]["stop_managed_status"],
            "pending_validated_high_resolution_stop_path",
        )

    def test_refuses_snapshot_before_exit_candle_matures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = self.make_archive(
                Path(directory), "2026-08-03T14:29:00+00:00"
            )
            with self.assertRaisesRegex(ValueError, "before the exit"):
                build_outcomes(
                    submissions=[self.submission()],
                    archive=archive,
                    decision_date="2026-08-03",
                    horizon="60m",
                )

    def test_append_is_idempotent_and_summary_is_equal_weighted(self) -> None:
        rows = [
            {
                "round_id": "r1",
                "participant": "Jeff",
                "decision_date": "2026-08-03",
                "symbol": "AAA",
                "horizon": "20m",
                "unmanaged_net_return_pct": 1.0,
                "status": "complete_unmanaged",
            },
            {
                "round_id": "r1",
                "participant": "Jeff",
                "decision_date": "2026-08-03",
                "symbol": "BBB",
                "horizon": "20m",
                "unmanaged_net_return_pct": -0.5,
                "status": "complete_unmanaged",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "outcomes.jsonl"
            self.assertEqual(append_unique(path, rows), 2)
            self.assertEqual(append_unique(path, rows), 0)
            payload = summarize(
                [json.loads(line) for line in path.read_text().splitlines()]
            )
        record = payload["records"][0]
        self.assertEqual(record["picks"], 2)
        self.assertAlmostEqual(
            record["equal_weight_basket_net_return_pct"], 0.25
        )


if __name__ == "__main__":
    unittest.main()
