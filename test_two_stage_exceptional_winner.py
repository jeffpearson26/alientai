from __future__ import annotations

import unittest
from datetime import datetime, timezone

from train_two_stage_exceptional_winner import apply_gate, choose_gate, split_rows, targets


def milliseconds(day: str) -> int:
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1000)


class TwoStageExceptionalWinnerTests(unittest.TestCase):
    def test_split_has_embargoes_and_untouched_test(self):
        rows = [{"market_date": f"2026-01-{day:02d}"} for day in range(1, 31)]
        train, validation, test = split_rows(rows, milliseconds("2026-01-10"), milliseconds("2026-01-22"), 2)
        self.assertEqual(train[-1]["market_date"], "2026-01-08")
        self.assertEqual(validation[0]["market_date"], "2026-01-12")
        self.assertEqual(validation[-1]["market_date"], "2026-01-20")
        self.assertEqual(test[0]["market_date"], "2026-01-24")

    def test_targets_subtract_cost_and_clip_outliers(self):
        positive, returns = targets([
            {"label_forward_return_5d_pct": 0.20},
            {"label_forward_return_5d_pct": 50.0},
        ], 0.25)
        self.assertEqual(positive.tolist(), [0, 1])
        self.assertEqual(returns.tolist(), [-0.05000000074505806, 20.0])

    def test_gate_requires_all_three_models_to_agree(self):
        gate = {"discovery_threshold": 0.7, "positive_threshold": 0.55, "expected_return_threshold": 0.5}
        base = {
            "symbol": "A", "market_date": "2026-01-01", "future_market_date": "2026-01-08",
            "label_forward_return_5d_pct": 12.0,
        }
        rows = [
            {**base, "raw_score": 0.8, "positive_net_probability": 0.6, "expected_net_return_pct": 0.7},
            {**base, "symbol": "B", "raw_score": 0.8, "positive_net_probability": 0.5, "expected_net_return_pct": 0.7},
        ]
        self.assertEqual([row["symbol"] for row in apply_gate(rows, gate)], ["A"])

    def test_gate_selection_uses_minimum_signal_requirement(self):
        rows = []
        for index in range(120):
            rows.append({
                "symbol": f"S{index}", "market_date": "2026-01-01", "future_market_date": "2026-01-08",
                "raw_score": 0.81, "positive_net_probability": 0.58, "expected_net_return_pct": 0.8,
                "label_forward_return_5d_pct": 11.0 if index < 20 else 1.0,
            })
        gate, _ = choose_gate(rows, 0.25, minimum_signals=100)
        self.assertGreaterEqual(gate["discovery_threshold"], 0.65)


if __name__ == "__main__":
    unittest.main()
