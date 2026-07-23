from __future__ import annotations

import unittest

from evaluate_unusual_call_contexts import context_slices


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


if __name__ == "__main__":
    unittest.main()
