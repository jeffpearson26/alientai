import csv
import gzip
import tempfile
import unittest
from pathlib import Path

from audit_russell_listing_status_coverage import audit


def write_snapshot(path: Path, rows: list[dict[str, str]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["symbol", "assetType", "status"])
        writer.writeheader()
        writer.writerows(rows)


class RussellListingStatusCoverageTests(unittest.TestCase):
    def test_reports_active_legacy_presence_without_claiming_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_snapshot(root / "listing_status_active_2020-06-30.csv.gz", [
                {"symbol": "AAA", "assetType": "Stock", "status": "Active"},
                {"symbol": "ETF1", "assetType": "ETF", "status": "Active"},
                {"symbol": "OLD", "assetType": "Stock", "status": "Delisted"},
            ])
            report = audit(root, {"AAA", "BBB", "OLD"}, {"AAA"})
        snapshot = report["snapshots"][0]
        self.assertEqual(snapshot["legacy_symbols_present_as_active_stocks"], 1)
        self.assertEqual(snapshot["legacy_symbols_absent_from_active_snapshot"], 2)
        self.assertEqual(snapshot["legacy_active_current_sp500_overlap"], 1)


if __name__ == "__main__":
    unittest.main()
