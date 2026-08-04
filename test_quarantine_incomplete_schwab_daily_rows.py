from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from quarantine_incomplete_schwab_daily_rows import plan_quarantine


class QuarantineIncompleteSchwabDailyRowsTests(unittest.TestCase):
    def write(self, path: Path, dates: list[str]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["symbol", "date", "close"])
            writer.writeheader()
            for day in dates:
                writer.writerow({"symbol": "AAA", "date": day, "close": "1"})

    def test_only_final_target_row_can_be_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AAA.csv"
            self.write(path, ["2026-08-02", "2026-08-03"])
            remaining, record = plan_quarantine(path, "2026-08-03")
            self.assertEqual([row["date"] for row in remaining], ["2026-08-02"])
            self.assertEqual(record["row"]["date"], "2026-08-03")

    def test_nonfinal_target_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AAA.csv"
            self.write(path, ["2026-08-02", "2026-08-03", "2026-08-04"])
            with self.assertRaises(ValueError):
                plan_quarantine(path, "2026-08-03")


if __name__ == "__main__":
    unittest.main()
