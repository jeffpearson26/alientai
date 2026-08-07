from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from train_contextual_options_next_session_clone import (
    choose_daily_candidates,
    evidence_gate,
    maybe_open_sealed_test,
    read_rows_for_dates,
)


class ContextualOptionsNextSessionCloneTests(unittest.TestCase):
    def test_daily_rule_uses_top_quarter_and_caps_at_five(self) -> None:
        rows = []
        scores = []
        for index in range(400):
            rows.append(
                {
                    "symbol": f"S{index:03d}",
                    "market_date": "2026-01-02",
                    "option_chain_available": True,
                    "option_contract_count": 1,
                    "call_volume_unusual": index >= 390,
                    "label_forward_return_1d_pct": 1.0,
                }
            )
            scores.append(float(index))
        selected, audit = choose_daily_candidates(rows, scores)
        self.assertEqual(len(selected), 5)
        self.assertEqual(
            [row["symbol"] for row in selected],
            ["S399", "S398", "S397", "S396", "S395"],
        )
        self.assertEqual(audit[0]["state"], "COMPLETE")

    def test_incomplete_universe_abstains(self) -> None:
        rows = [
            {
                "symbol": "AAA",
                "market_date": "2026-01-02",
                "option_chain_available": True,
                "option_contract_count": 1,
                "call_volume_unusual": True,
                "label_forward_return_1d_pct": 1.0,
            }
        ]
        selected, audit = choose_daily_candidates(rows, [1.0])
        self.assertEqual(selected, [])
        self.assertEqual(audit[0]["state"], "INCOMPLETE_UNIVERSE")

    def test_failed_gate_does_not_call_sealed_loader(self) -> None:
        called = False

        def loader():
            nonlocal called
            called = True
            return {}

        status, test = maybe_open_sealed_test(
            {
                "signals": 29,
                "decision_dates": 10,
                "mean_net_return_pct": 1.0,
                "median_net_return_pct": 1.0,
                "win_rate_pct": 60.0,
            },
            loader,
        )
        self.assertFalse(called)
        self.assertEqual(status, "RESEARCH_HOLD")
        self.assertEqual(test["status"], "SEALED_UNLOADED")

    def test_gate_matches_frozen_evidence_contract(self) -> None:
        result = evidence_gate(
            {
                "signals": 30,
                "decision_dates": 10,
                "mean_net_return_pct": 0.1,
                "median_net_return_pct": 0.01,
                "win_rate_pct": 50.0,
            }
        )
        self.assertTrue(result["passed"])

    def test_nonselected_json_is_never_decoded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "panel.jsonl"
            selected = {
                "market_date": "2026-01-02",
                "symbol": "AAA",
                "label_forward_return_1d_pct": 1.0,
            }
            path.write_bytes(
                (
                    json.dumps(selected, separators=(",", ":"))
                    + "\n"
                    + '{"market_date":"2026-07-01","sealed": INVALID}\n'
                ).encode("utf-8")
            )
            rows = read_rows_for_dates(path, {"2026-01-02"})
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["symbol"], "AAA")


if __name__ == "__main__":
    unittest.main()
