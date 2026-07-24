import csv
import tempfile
import unittest
from pathlib import Path

from audit_russell_archive_coverage import audit_archive


def write_csv(path: Path, symbol: str, dates: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["symbol", "date"])
        writer.writeheader()
        for date in dates:
            writer.writerow({"symbol": symbol, "date": date})


class RussellArchiveAuditTests(unittest.TestCase):
    def test_reports_missing_and_sp500_overlap_without_mutating_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_csv(root / "AAA_schwab_1d_max.csv", "AAA", ["2026-01-02", "2026-07-09"])
            write_csv(root / "BBB_schwab_1d_max.csv", "BBB", ["2026-01-02", "2026-07-08"])
            report = audit_archive(root, {"AAA", "BBB", "MISSING"}, {"AAA"})
        self.assertEqual(report["symbols_with_usable_daily_history"], 2)
        self.assertEqual(report["symbols_missing_or_empty"], 1)
        self.assertEqual(report["sp500_symbol_overlap"], 1)
        self.assertEqual(report["newest_local_daily_date"], "2026-07-09")
        self.assertEqual(report["missing_or_empty_symbols"], ["MISSING"])


if __name__ == "__main__":
    unittest.main()
