from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from evaluate_nasdaq_prospective_outcomes import (
    append_unique,
    build_outcomes,
    summarize,
)


class NasdaqProspectiveOutcomeTests(unittest.TestCase):
    def write_history(self, root: Path) -> None:
        path = root / "AAA_schwab_1d_max.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=("symbol", "date", "close"),
            )
            writer.writeheader()
            for day, close in (
                ("2026-07-26", 100),
                ("2026-07-27", 101),
                ("2026-07-28", 102),
                ("2026-07-29", 103),
                ("2026-07-30", 104),
                ("2026-08-02", 105),
            ):
                writer.writerow({"symbol": "AAA", "date": day, "close": close})

    def observation(self) -> dict:
        return {
            "model_id": "model",
            "model_sha256": "hash",
            "symbol": "AAA",
            "market_date": "2026-07-26",
            "market_session_date": "2026-07-27",
            "entry_close": 100,
            "target_horizon_sessions": 5,
        }

    def test_requires_fifth_later_session_and_maps_legacy_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_history(root)
            complete, pending = build_outcomes(
                observations=[self.observation()],
                daily_dir=root,
                as_of_session_date="2026-08-03",
            )
        self.assertEqual(len(complete), 1)
        self.assertFalse(pending)
        self.assertEqual(complete[0]["exit_session_date"], "2026-08-03")
        self.assertAlmostEqual(complete[0]["net_return_pct"], 4.75)

    def test_missing_fifth_session_remains_pending(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_history(root)
            path = root / "AAA_schwab_1d_max.csv"
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
            complete, pending = build_outcomes(
                observations=[self.observation()],
                daily_dir=root,
                as_of_session_date="2026-08-03",
            )
        self.assertFalse(complete)
        self.assertEqual(pending[0]["status"], "pending_candle_coverage")

    def test_rejects_changed_entry_close(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_history(root)
            observation = self.observation()
            observation["entry_close"] = 99
            with self.assertRaisesRegex(ValueError, "entry close changed"):
                build_outcomes(
                    observations=[observation],
                    daily_dir=root,
                    as_of_session_date="2026-08-03",
                )

    def test_append_is_idempotent_and_summary_counts_dates(self) -> None:
        row = {
            "model_id": "model",
            "symbol": "AAA",
            "entry_market_date": "2026-07-26",
            "entry_session_date": "2026-07-27",
            "target_horizon_sessions": 5,
            "net_return_pct": 1.0,
            "status": "complete",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "outcomes.jsonl"
            self.assertEqual(append_unique(path, [row]), 1)
            self.assertEqual(append_unique(path, [row]), 0)
            rows = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
            ]
            payload = summarize(rows)
        self.assertEqual(payload["records"][0]["signals"], 1)
        self.assertEqual(payload["records"][0]["decision_dates"], 1)


if __name__ == "__main__":
    unittest.main()
