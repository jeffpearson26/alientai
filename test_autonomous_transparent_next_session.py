from __future__ import annotations

import unittest

import evaluate_autonomous_transparent_next_session as clone


class AutonomousTransparentNextSessionTests(unittest.TestCase):
    def test_clone_constants_are_one_session_and_research_only(self) -> None:
        self.assertEqual(clone.research.HORIZON_SESSIONS, 1)
        self.assertEqual(clone.research.EMBARGO_SESSIONS, 1)
        self.assertEqual(clone.research.HAC_LAG_SESSIONS, 0)
        self.assertEqual(clone.research.TARGET, "label_1d_net_return_pct")
        self.assertEqual(
            clone.research.LABEL_END, "label_1d_exit_market_date"
        )
        self.assertEqual(
            clone.research.PORTFOLIO_SLOTS,
            clone.research.MAX_DAILY_SELECTIONS,
        )

    def test_formula_is_identical_to_source_formula(self) -> None:
        rows = [
            {
                "rank_relative_to_qqq_126d_pct": 0.8,
                "rank_relative_to_qqq_60d_pct": 0.6,
                "rank_lh_realized_volatility_60d_pct": 0.2,
            }
        ]
        score = clone.source.score_rows(rows)
        self.assertAlmostEqual(float(score[0]), 0.74)


if __name__ == "__main__":
    unittest.main()
