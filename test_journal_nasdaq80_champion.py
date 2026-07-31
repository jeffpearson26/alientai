import csv
import tempfile
import unittest
from pathlib import Path

from journal_nasdaq80_champion import latest_universe_common_date


def write_dates(path: Path, dates: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date"])
        writer.writeheader()
        writer.writerows({"date": value} for value in dates)


class Nasdaq80ChampionJournalTests(unittest.TestCase):
    def test_latest_common_date_requires_every_frozen_symbol(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_dates(root / "A_schwab_1d_max.csv", ["2026-07-28", "2026-07-29"])
            write_dates(root / "B_schwab_1d_max.csv", ["2026-07-27", "2026-07-28"])
            self.assertEqual(
                latest_universe_common_date(root, ["A", "B"]),
                "2026-07-28",
            )

    def test_missing_frozen_symbol_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "missing daily history"):
                latest_universe_common_date(Path(folder), ["A"])


if __name__ == "__main__":
    unittest.main()
