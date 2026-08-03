from __future__ import annotations

import csv
import gzip
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from download_alpha_vantage_matched_premarket import archive_path
from evaluate_intraday_prospective_outcomes import completed_outcomes


class IntradayProspectiveOutcomeTests(unittest.TestCase):
    def make_archive(
        self,
        root: Path,
        *,
        mode: str = "current",
        entitlement: str = "realtime",
        status: str = "complete",
    ) -> Path:
        archive = root / "archive"
        archive.mkdir()
        manifest = {
            "status": status,
            "mode": mode,
            "entitlement": entitlement,
            "current_date": "2026-08-03",
            "bar_interval_minutes": 5,
            "timestamp_convention": "interval_start",
            "updated_at_utc": "2026-08-03T14:31:00+00:00",
        }
        (archive / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        path = archive_path(archive, "AAA", "2026-08")
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(
            path, "wt", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=(
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ),
            )
            writer.writeheader()
            cursor = datetime(2026, 8, 3, 9, 30)
            final = datetime(2026, 8, 3, 10, 25)
            while cursor <= final:
                writer.writerow(
                    {
                        "timestamp": cursor.strftime("%Y-%m-%d %H:%M:%S"),
                        "open": 100,
                        "high": 103,
                        "low": 99,
                        "close": 102,
                        "volume": 10,
                    }
                )
                cursor += timedelta(minutes=5)
        return archive

    @staticmethod
    def observation(horizon: int = 60) -> dict:
        return {
            "model_id": "frozen-model",
            "model_sha256": "abc",
            "market_date": "2026-08-03",
            "symbol": "AAA",
            "rank": 1,
            "model_score": 0.5,
            "horizon_minutes": horizon,
        }

    def test_accepts_only_completed_current_realtime_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = self.make_archive(Path(directory))
            rows = completed_outcomes([self.observation()], archive)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_mode"], "current")
        self.assertEqual(rows[0]["source_entitlement"], "realtime")
        self.assertEqual(len(rows[0]["source_manifest_sha256"]), 64)

    def test_rejects_historical_archive_for_frozen_realtime_study(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = self.make_archive(
                Path(directory),
                mode="historical",
                entitlement="historical",
            )
            with self.assertRaisesRegex(ValueError, "current realtime"):
                completed_outcomes([self.observation()], archive)

    def test_rejects_failed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = self.make_archive(
                Path(directory),
                status="failed_closed",
            )
            with self.assertRaisesRegex(ValueError, "manifest mismatch"):
                completed_outcomes([self.observation()], archive)

    def test_rejects_empty_observation_batch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = self.make_archive(Path(directory))
            with self.assertRaisesRegex(ValueError, "no valid pre-entry"):
                completed_outcomes([], archive)


if __name__ == "__main__":
    unittest.main()
