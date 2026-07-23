from __future__ import annotations

import unittest

from evaluate_unusual_call_contexts import context_slices
from evaluate_unusual_call_outcomes import join_option_outcomes


class UnusualCallContextTests(unittest.TestCase):
    def test_keeps_unusual_calls_only_in_requested_context(self):
        rows = [
            {"symbol": "A", "technical_context_score": 0.1, "call_volume_unusual": True},
            {"symbol": "B", "technical_context_score": 0.5, "call_volume_unusual": False},
            {"symbol": "C", "technical_context_score": 0.9, "call_volume_unusual": True},
            {"symbol": "D", "technical_context_score": 1.0, "call_volume_unusual": True},
        ]
        report = context_slices(rows, fractions=(0.5,))
        self.assertEqual({"C", "D"}, {row["symbol"] for row in report[0]["rows"]})

    def test_rejects_invalid_fraction(self):
        with self.assertRaises(ValueError):
            context_slices([{"technical_context_score": 0.1, "call_volume_unusual": True}], fractions=(0.0,))

    def test_preserves_precomputed_leakage_safe_call_features(self):
        rows = join_option_outcomes(
            [{"symbol": "A", "market_date": "2026-01-02", "label_forward_return_5d_pct": 1.0}],
            [{"symbol": "A", "market_date": "2026-01-02", "call_activity_history_count": 20,
              "call_volume_unusual": True}],
        )
        self.assertTrue(rows[0]["call_volume_unusual"])
        self.assertEqual(rows[0]["call_activity_history_count"], 20)


if __name__ == "__main__":
    unittest.main()
