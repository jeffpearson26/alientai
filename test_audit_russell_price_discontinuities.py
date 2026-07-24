import csv
import tempfile
import unittest
from pathlib import Path

from audit_russell_price_discontinuities import find_discontinuities, read_candles


class RussellPriceDiscontinuityTests(unittest.TestCase):
    def test_reports_extreme_move_with_exact_dates_and_prices(self):
        candles = [
            {"date": "2026-01-02", "close": "10"},
            {"date": "2026-01-05", "close": "16"},
            {"date": "2026-01-06", "close": "16"},
        ]
        findings, skipped = find_discontinuities("TEST", candles, threshold_pct=50.0, horizon_days=1)
        self.assertEqual(len(findings), 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(findings[0]["start_date"], "2026-01-02")
        self.assertEqual(findings[0]["end_date"], "2026-01-05")
        self.assertEqual(findings[0]["change_pct"], 60.0)

    def test_ignores_small_moves_and_invalid_prices(self):
        candles = [
            {"date": "2026-01-02", "close": "0"},
            {"date": "2026-01-05", "close": "10"},
            {"date": "2026-01-06", "close": "12"},
        ]
        self.assertEqual(find_discontinuities("TEST", candles, threshold_pct=50.0, horizon_days=1)[0], [])

    def test_skips_long_date_gap_instead_of_calling_it_one_day_return(self):
        candles = [
            {"date": "2026-01-02", "close": "10"},
            {"date": "2026-06-02", "close": "30"},
        ]
        findings, skipped = find_discontinuities("TEST", candles, threshold_pct=50.0, horizon_days=1)
        self.assertEqual(findings, [])
        self.assertEqual(skipped, 1)

    def test_reader_sorts_legacy_rows_before_comparing_adjacent_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["date", "close"])
                writer.writeheader()
                writer.writerows([{"date": "2026-01-05", "close": "12"}, {"date": "2026-01-02", "close": "10"}])
            rows = read_candles(path)
        self.assertEqual([row["date"] for row in rows], ["2026-01-02", "2026-01-05"])


if __name__ == "__main__":
    unittest.main()
