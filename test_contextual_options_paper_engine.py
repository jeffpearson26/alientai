from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alientai_v2.engines.contextual_options_paper import scan


class ContextualOptionsPaperEngineTests(unittest.TestCase):
    def test_missing_same_day_payload_fails_closed(self) -> None:
        rows = scan([], {"contextual_options_daily_payload_path": "missing.json"})
        self.assertEqual(rows[0]["decision"], "AVOID")

    def test_complete_same_day_payload_can_emit_paper_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            path.write_text(json.dumps({
                "status": "research_payload_ready",
                "research_only": True,
                "market_date": "2026-07-28",
                "universe_rows": 481,
                "candidates": [{
                    "symbol": "AAA",
                    "shadow_policy_id": "contextual_options_shadow_v1",
                    "shadow_research_decision": "BUY_CANDIDATE",
                    "technical_context_score": 0.8,
                }],
            }), encoding="utf-8")
            fake_now = type("FakeDateTime", (), {
                "now": staticmethod(lambda _tz: __import__("datetime").datetime(2026, 7, 28, 8, 0))
            })
            with patch("alientai_v2.engines.contextual_options_paper.datetime", fake_now):
                rows = scan(
                    [{"symbol": "AAA", "price": 100.0}],
                    {"contextual_options_daily_payload_path": str(path)},
                )
        self.assertEqual(rows[0]["decision"], "BUY_CANDIDATE")
        self.assertEqual(rows[0]["engine_id"], "contextual_options_shadow_v1")

    def test_stale_payload_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            path.write_text(json.dumps({
                "status": "research_payload_ready", "research_only": True,
                "market_date": "2026-07-21", "universe_rows": 481, "candidates": [],
            }), encoding="utf-8")
            rows = scan([], {"contextual_options_daily_payload_path": str(path)})
        self.assertEqual(rows[0]["decision"], "AVOID")

    def test_prior_session_payload_can_emit_paper_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            path.write_text(json.dumps({
                "status": "research_payload_ready", "research_only": True,
                "market_date": "2026-07-27", "universe_rows": 481,
                "candidates": [{
                    "symbol": "AAA",
                    "shadow_policy_id": "contextual_options_shadow_v1",
                    "shadow_research_decision": "BUY_CANDIDATE",
                    "technical_context_score": 0.8,
                }],
            }), encoding="utf-8")
            fake_now = type("FakeDateTime", (), {
                "now": staticmethod(lambda _tz: __import__("datetime").datetime(2026, 7, 28, 8, 0))
            })
            with patch("alientai_v2.engines.contextual_options_paper.datetime", fake_now):
                rows = scan(
                    [{"symbol": "AAA", "price": 100.0}],
                    {"contextual_options_daily_payload_path": str(path)},
                )
        self.assertEqual(rows[0]["decision"], "BUY_CANDIDATE")


if __name__ == "__main__":
    unittest.main()
