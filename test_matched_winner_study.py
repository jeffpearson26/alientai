from __future__ import annotations

import unittest

from alientai_v2.research.matched_winner_study import (
    build_matched_study, feature_contrasts, match_distance, select_non_overlapping_winners,
)


def row(symbol, day, forward, price=100, volatility=1.0, lag=0.0, sector="tech"):
    return {
        "symbol": symbol, "market_date": f"2026-01-{day:02d}", "close": price,
        "realized_volatility_20d_pct": volatility, "return_20d_lag_pct": lag,
        "sector": sector, "label_forward_return_5d_pct": forward,
    }


class MatchedWinnerStudyTests(unittest.TestCase):
    def test_overlapping_winners_for_same_symbol_are_suppressed(self):
        winners = select_non_overlapping_winners(
            [row("A", 1, 6), row("A", 5, 8), row("A", 12, 7)],
            winner_return_pct=5, minimum_calendar_gap_days=9,
        )
        self.assertEqual([item["market_date"] for item in winners], ["2026-01-01", "2026-01-12"])

    def test_controls_are_from_same_date_and_below_ceiling(self):
        rows = [
            row("WIN", 10, 6), row("GOOD", 10, 0), row("TOO_HIGH", 10, 2),
            row("WRONG_DAY", 11, 0),
        ]
        study = build_matched_study(rows, winner_return_pct=5, maximum_control_return_pct=1, controls_per_winner=5)
        controls = [item for item in study if item["study_role"] == "control"]
        self.assertEqual([item["symbol"] for item in controls], ["GOOD"])

    def test_closest_control_is_selected(self):
        winner = row("WIN", 10, 6, price=100, volatility=2, lag=3)
        close = row("CLOSE", 10, 0, price=101, volatility=2.1, lag=3.2)
        far = row("FAR", 10, 0, price=10, volatility=8, lag=-20, sector="energy")
        study = build_matched_study([winner, far, close], controls_per_winner=1)
        self.assertEqual(study[1]["symbol"], "CLOSE")
        self.assertLess(match_distance(winner, close), match_distance(winner, far))

    def test_future_outcome_is_not_used_in_match_distance(self):
        winner = row("WIN", 10, 6)
        control_a = row("A", 10, -20)
        control_b = row("B", 10, 1)
        self.assertEqual(match_distance(winner, control_a), match_distance(winner, control_b))

    def test_invalid_control_ceiling_fails_closed(self):
        with self.assertRaises(ValueError):
            build_matched_study([], winner_return_pct=5, maximum_control_return_pct=5)

    def test_feature_contrast_rejects_future_outcome_label(self):
        with self.assertRaises(ValueError):
            feature_contrasts([], features=["label_forward_return_5d_pct"])

    def test_feature_contrast_reports_pre_event_difference(self):
        rows = [
            {"study_role": "winner", "return_5d_lag_pct": 4.0},
            {"study_role": "winner", "return_5d_lag_pct": 6.0},
            {"study_role": "control", "return_5d_lag_pct": 0.0},
            {"study_role": "control", "return_5d_lag_pct": 2.0},
        ]
        result = feature_contrasts(rows, features=["return_5d_lag_pct"])[0]
        self.assertEqual(result["winner_mean"], 5.0)
        self.assertEqual(result["control_mean"], 1.0)
        self.assertGreater(result["standardized_mean_difference"], 0)


if __name__ == "__main__":
    unittest.main()
