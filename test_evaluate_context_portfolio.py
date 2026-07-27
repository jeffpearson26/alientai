from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from datetime import date

from evaluate_context_portfolio import (
    capital_scaled_drawdown,
    capacity_limited,
    daily_archive_sha256,
    file_sha256,
    split_chronologically,
)


class ContextPortfolioTests(unittest.TestCase):
    def test_split_has_embargo_between_calibration_and_test(self):
        rows = [{"market_date": f"2026-01-{day:02d}"} for day in range(1, 11)]
        calibration, test = split_chronologically(rows, 0.6, 2)
        self.assertLess(max(row["market_date"] for row in calibration), min(row["market_date"] for row in test))
        self.assertEqual("2026-01-09", min(row["market_date"] for row in test))

    def test_capacity_prevents_overlapping_entries(self):
        rows = [
            {"market_date": "2026-01-01", "future_market_date": "2026-01-05", "technical_context_score": 0.9},
            {"market_date": "2026-01-02", "future_market_date": "2026-01-06", "technical_context_score": 0.8},
            {"market_date": "2026-01-06", "future_market_date": "2026-01-10", "technical_context_score": 0.7},
        ]
        self.assertEqual(["2026-01-01", "2026-01-06"], [row["market_date"] for row in capacity_limited(rows, 1)])

    def test_file_hash_changes_when_artifact_changes(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.txt"
            path.write_text("first", encoding="utf-8")
            first = file_sha256(path)
            path.write_text("second", encoding="utf-8")
            self.assertNotEqual(first, file_sha256(path))

    def test_capital_scaled_curve_leaves_unused_slots_in_cash(self):
        closes = {"AAA": {
            date(2026, 1, 2): 100.0,
            date(2026, 1, 5): 80.0,
        }}
        rows = [{
            "symbol": "AAA",
            "market_date": "2026-01-02",
            "future_market_date": "2026-01-05",
        }]
        metrics = capital_scaled_drawdown(rows, closes, 5, 0.0)
        self.assertEqual(-4.0, metrics["capital_scaled_max_drawdown_pct"])
        self.assertEqual(-4.0, metrics["capital_scaled_final_return_pct"])
        self.assertEqual(1, metrics["capital_scaled_peak_open_positions"])

    def test_capital_scaled_curve_subtracts_cost_from_deployed_slot(self):
        closes = {"AAA": {
            date(2026, 1, 2): 100.0,
            date(2026, 1, 5): 100.0,
        }}
        rows = [{
            "symbol": "AAA",
            "market_date": "2026-01-02",
            "future_market_date": "2026-01-05",
        }]
        metrics = capital_scaled_drawdown(rows, closes, 5, 0.25)
        self.assertEqual(-0.05, metrics["capital_scaled_final_return_pct"])

    def test_local_schwab_archive_date_is_mapped_to_us_session(self):
        from evaluate_context_portfolio import load_daily_closes
        with TemporaryDirectory() as directory:
            path = Path(directory) / "AAA_schwab_1d_max.csv"
            path.write_text(
                "symbol,date,close\nAAA,2026-01-04,100\n",
                encoding="utf-8",
            )
            closes = load_daily_closes(Path(directory))
        self.assertEqual(100.0, closes["AAA"][date(2026, 1, 5)])

    def test_daily_archive_fingerprint_changes_with_price_content(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "AAA_schwab_1d_max.csv"
            path.write_text("symbol,date,close\nAAA,2026-01-04,100\n", encoding="utf-8")
            first = daily_archive_sha256(Path(directory))
            path.write_text("symbol,date,close\nAAA,2026-01-04,101\n", encoding="utf-8")
            self.assertNotEqual(first, daily_archive_sha256(Path(directory)))


if __name__ == "__main__":
    unittest.main()
