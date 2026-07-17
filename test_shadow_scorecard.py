from __future__ import annotations

import unittest

from alientai_v2.shadow_scorecard import summarize_engine_outcomes


def rows(engine, values):
    return [{"engine_id": engine, "raw_return_pct": value + 0.25, "net_return_pct": value} for value in values]


class ShadowScorecardTests(unittest.TestCase):
    def test_small_sample_is_insufficient(self):
        card = summarize_engine_outcomes(rows("small", [1.0, -0.5]), min_completed_signals=3)[0]
        self.assertEqual("INSUFFICIENT_DATA", card["classification"])

    def test_profitable_engine_can_research_pass(self):
        card = summarize_engine_outcomes(rows("good", [2.0, 1.0, -0.5]), min_completed_signals=3)[0]
        self.assertEqual("RESEARCH_PASS", card["classification"])
        self.assertEqual(6.0, card["profit_factor"])

    def test_negative_engine_fails(self):
        card = summarize_engine_outcomes(rows("bad", [0.5, -1.0, -1.0]), min_completed_signals=3)[0]
        self.assertEqual("FAILED", card["classification"])

    def test_scorecard_never_enables_trading(self):
        card = summarize_engine_outcomes(rows("good", [2.0, 1.0, -0.5]), min_completed_signals=3)[0]
        self.assertFalse(card["auto_trading_enabled"])


if __name__ == "__main__":
    unittest.main()
