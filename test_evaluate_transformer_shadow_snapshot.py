from __future__ import annotations

import unittest

from evaluate_transformer_shadow_snapshot import completed_return


class TransformerShadowOutcomeTests(unittest.TestCase):
    def test_uses_exact_forward_horizon_without_future_substitution(self) -> None:
        rows = [{"date": "2026-01-01", "close": "100"}, {"date": "2026-01-02", "close": "110"}, {"date": "2026-01-03", "close": "121"}]
        self.assertEqual(round(completed_return(rows, "2026-01-01", 2) or 0, 6), 21.0)

    def test_missing_horizon_candle_fails_closed(self) -> None:
        rows = [{"date": "2026-01-01", "close": "100"}]
        self.assertIsNone(completed_return(rows, "2026-01-01", 20))


if __name__ == "__main__":
    unittest.main()
