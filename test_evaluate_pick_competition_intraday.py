from __future__ import annotations

import csv
import gzip
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from download_alpha_vantage_matched_premarket import archive_path
from evaluate_pick_competition_intraday import (
    append_unique,
    build_outcomes,
    summarize,
)


class PickCompetitionIntradayOutcomeTests(unittest.TestCase):
    def make_archive(
        self, root: Path, updated: str, *, mode: str = "current"
    ) -> Path:
        archive = root / "archive"
        archive.mkdir()
        manifest = {
            "status": "complete",
            "mode": mode,
            "entitlement": "realtime" if mode == "current" else "historical",
            "bar_interval_minutes": 5,
            "timestamp_convention": "interval_start",
            "updated_at_utc": updated,
        }
        if mode == "current":
            manifest["current_date"] = "2026-08-03"
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
            cursor = datetime(2026, 8, 3, 9, 30)
            final = datetime(2026, 8, 3, 10, 25)
            while cursor <= final:
                stamp = cursor.strftime("%Y-%m-%d %H:%M:%S")
                close = 102 if stamp.endswith("09:45:00") else 101
                if stamp.endswith("10:25:00"):
                    close = 103
                writer.writerow(
                    {
                        "timestamp": stamp,
                        "open": 100,
                        "high": max(102, close),
                        "low": 99,
                        "close": close,
                        "volume": 10,
                    }
                )
                cursor += timedelta(minutes=5)
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
            "complete_5minute_observable",
        )
        self.assertFalse(rows[0]["stop_applied"])
        self.assertAlmostEqual(rows[0]["stop_managed_net_return_pct"], 2.75)

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

    def test_accepts_completed_historical_archive_for_frozen_picks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = self.make_archive(
                Path(directory),
                "2026-08-04T02:00:00+00:00",
                mode="historical",
            )
            rows = build_outcomes(
                submissions=[self.submission()],
                archive=archive,
                decision_date="2026-08-03",
                horizon="20m",
            )
        self.assertEqual(rows[0]["unmanaged_exit_price"], 102)
        self.assertTrue(rows[0]["source"].endswith("historical"))

    def test_append_is_idempotent_and_summary_is_equal_weighted(self) -> None:
        rows = [
            {
                "round_id": "r1",
                "participant": "Jeff",
                "decision_date": "2026-08-03",
                "symbol": "AAA",
                "horizon": "20m",
                "unmanaged_net_return_pct": 1.0,
                "stop_managed_net_return_pct": 0.5,
                "status": "complete_unmanaged",
            },
            {
                "round_id": "r1",
                "participant": "Jeff",
                "decision_date": "2026-08-03",
                "symbol": "BBB",
                "horizon": "20m",
                "unmanaged_net_return_pct": -0.5,
                "stop_managed_net_return_pct": -0.25,
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
            record["unmanaged_equal_weight_basket_net_return_pct"], 0.25
        )
        self.assertAlmostEqual(
            record["stop_managed_equal_weight_basket_net_return_pct"], 0.125
        )

    def test_intrabar_stop_crossing_uses_next_bar_open(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = self.make_archive(
                root, "2026-08-03T14:31:00+00:00"
            )
            path = archive_path(archive, "AAA", "2026-08")
            with gzip.open(
                path, "rt", encoding="utf-8", newline=""
            ) as handle:
                rows = list(csv.DictReader(handle))
            by_timestamp = {row["timestamp"]: row for row in rows}
            by_timestamp["2026-08-03 09:35:00"].update(
                {"open": "99", "high": "100", "low": "94", "close": "96"}
            )
            by_timestamp["2026-08-03 09:40:00"].update(
                {"open": "93", "high": "95", "low": "92", "close": "94"}
            )
            with gzip.open(
                path, "wt", encoding="utf-8", newline=""
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            outcomes = build_outcomes(
                submissions=[self.submission()],
                archive=archive,
                decision_date="2026-08-03",
                horizon="20m",
            )
        row = outcomes[0]
        self.assertTrue(row["stop_applied"])
        self.assertEqual(row["stop_managed_exit_price"], 93)
        self.assertEqual(
            row["stop_fill_rule"],
            "next_bar_open_after_completed_bar_crossing",
        )


if __name__ == "__main__":
    unittest.main()
