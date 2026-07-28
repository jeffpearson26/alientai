import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from journal_nasdaq_challengers import (
    append_unique,
    select_candidates,
    schwab_session_date,
    validate_market_date_freshness,
)


class NasdaqChallengerJournalTests(unittest.TestCase):
    def test_selection_enforces_cutoff_and_maximum(self):
        rows = [{"symbol": symbol} for symbol in ("A", "B", "C")]
        selected = select_candidates(rows, [0.1, 0.9, 0.8], 0.5, 1)
        self.assertEqual([row["symbol"] for row in selected], ["B"])
        self.assertEqual(selected[0]["confidence_rank_1_to_100"], 100)

    def test_append_is_idempotent_by_model_date_symbol(self):
        row = {"model_id": "m", "market_date": "2026-01-02", "symbol": "A"}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "journal.jsonl"
            self.assertEqual(append_unique(path, [row]), 1)
            self.assertEqual(append_unique(path, [row]), 0)
            self.assertEqual(
                len([line for line in path.read_text().splitlines() if line]), 1
            )

    def test_append_preserves_distinct_models(self):
        rows = [
            {"model_id": model, "market_date": "2026-01-02", "symbol": "A"}
            for model in ("one", "two")
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "journal.jsonl"
            self.assertEqual(append_unique(path, rows), 2)
            decoded = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual({row["model_id"] for row in decoded}, {"one", "two"})

    def test_stale_market_date_fails_closed(self):
        with self.assertRaises(ValueError):
            validate_market_date_freshness(
                "2026-01-01", date(2026, 1, 10), 3
            )
        self.assertEqual(
            validate_market_date_freshness(
                "2026-01-09", date(2026, 1, 10), 3
            ),
            1,
        )

    def test_legacy_schwab_key_maps_to_actual_session_date(self):
        self.assertEqual(schwab_session_date("2026-07-26"), "2026-07-27")


if __name__ == "__main__":
    unittest.main()
