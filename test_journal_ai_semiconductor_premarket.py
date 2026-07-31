import tempfile
import unittest
from pathlib import Path

import numpy as np

from journal_ai_semiconductor_premarket import append_unique, merge_features, rank_candidates


class AiSemiconductorJournalTests(unittest.TestCase):
    def test_merge_requires_exact_keys(self):
        technical = [{"symbol": "NVDA", "market_date": "2026-07-30"}]
        with self.assertRaisesRegex(ValueError, "keys must match"):
            merge_features(technical, [], "2026-07-30")

    def test_merge_requires_available_premarket(self):
        row = {"symbol": "NVDA", "market_date": "2026-07-30"}
        with self.assertRaisesRegex(ValueError, "premarket unavailable"):
            merge_features([row], [{**row, "premarket_available": False}], "2026-07-30")

    def test_rank_is_descending_and_limited(self):
        rows = [{"symbol": "A"}, {"symbol": "B"}, {"symbol": "C"}]
        selected = rank_candidates(rows, np.asarray([0.1, 0.9, 0.5]), 2)
        self.assertEqual([row["symbol"] for row in selected], ["B", "C"])

    def test_append_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.jsonl"
            row = {"model_id": "m", "market_date": "2026-07-30", "symbol": "NVDA"}
            self.assertEqual(append_unique(path, [row]), 1)
            self.assertEqual(append_unique(path, [row]), 0)


if __name__ == "__main__":
    unittest.main()
