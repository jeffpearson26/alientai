import csv
import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from build_local_schwab_daily_technical_panel import build_panel, local_candles


class LocalSchwabDailyTechnicalPanelTests(unittest.TestCase):
    def test_reads_local_csv_and_builds_requested_snapshot(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "ABC_schwab_1d_max.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["date", "close", "high", "low", "volume"])
                writer.writeheader()
                for day in range(60):
                    writer.writerow({"date": (date(2026, 1, 1) + timedelta(days=day)).isoformat(), "close": 100 + day, "high": 101 + day, "low": 99 + day, "volume": 1000})
            rows, missing = build_panel("2026-03-01", ["ABC"], root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(missing, [])
            self.assertEqual(rows[0]["source"], "schwab_local_daily_csv")
            self.assertEqual(len(local_candles(path)), 60)


if __name__ == "__main__":
    unittest.main()
