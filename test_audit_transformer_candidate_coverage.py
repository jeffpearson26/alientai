from __future__ import annotations

import unittest

from audit_transformer_candidate_coverage import latest_date


class TransformerCandidateCoverageTests(unittest.TestCase):
    def test_uses_latest_candle_date(self) -> None:
        self.assertEqual(latest_date([{"date": "2026-07-20"}, {"date": "2026-07-21"}]), "2026-07-21")

    def test_empty_candles_have_no_date(self) -> None:
        self.assertEqual(latest_date([]), "")


if __name__ == "__main__":
    unittest.main()
