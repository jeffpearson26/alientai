from __future__ import annotations

import unittest

from train_selective_five_day_challenger import (
    chronological_split,
    daily_archive_sha256,
    file_sha256,
    outcome_metrics,
    sanitized_feature_row,
)
from pathlib import Path
import tempfile


class SelectiveFiveDayTrainerTests(unittest.TestCase):
    def test_sanitizer_removes_all_existing_outcomes(self):
        source = {
            "symbol": "aaa",
            "market_date": "2026-01-02",
            "as_of_utc": "2026-01-02T21:00:00+00:00",
            "technical_rsi_14": 50.0,
            "option_call_volume": 100.0,
            "label_forward_return_5d_pct": 10.0,
            "future_market_date": "2026-01-09",
        }
        result = sanitized_feature_row(source)
        self.assertEqual("AAA", result["symbol"])
        self.assertIn("technical_rsi_14", result)
        self.assertIn("option_call_volume", result)
        self.assertNotIn("label_forward_return_5d_pct", result)
        self.assertNotIn("future_market_date", result)

    def test_chronological_split_keeps_embargoes(self):
        rows = [
            {"market_date": f"2026-01-{day:02d}"}
            for day in range(1, 32)
        ]
        train, validation, test, summary = chronological_split(
            rows,
            train_fraction=0.50,
            validation_fraction=0.25,
            embargo_days=2,
        )
        self.assertTrue(len(train))
        self.assertTrue(len(validation))
        self.assertTrue(len(test))
        self.assertLess(max(train), min(validation))
        self.assertLess(max(validation), min(test))
        self.assertEqual(2, summary["embargo_calendar_days"])

    def test_empty_selection_metrics_are_explicit(self):
        self.assertEqual({"signals": 0}, outcome_metrics([]))

    def test_artifact_hashes_are_stable_and_content_sensitive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "AAA_schwab_1d_max.csv"
            first.write_text("symbol,date\nAAA,2026-01-02\n", encoding="utf-8")
            original = daily_archive_sha256(root)
            self.assertEqual(file_sha256(first), file_sha256(first))
            first.write_text("symbol,date\nAAA,2026-01-03\n", encoding="utf-8")
            self.assertNotEqual(original, daily_archive_sha256(root))


if __name__ == "__main__":
    unittest.main()
