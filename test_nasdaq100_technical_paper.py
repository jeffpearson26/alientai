import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from alientai_v2.engines import nasdaq100_technical_paper as subject


class NasdaqTechnicalPaperTests(unittest.TestCase):
    def payload(self, path: Path, **changes):
        today = datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()
        value = {
            "status": "paper_payload_ready", "research_only": True, "paper_only": True,
            "live_trading_enabled": False, "policy_id": subject.POLICY_ID,
            "market_date": today, "universe_rows": 80,
            "training_universe_size": 80,
            "training_universe_symbols": ["AAPL"] + [f"SYM{i:02d}" for i in range(79)],
            "candidates": [{
                "symbol": "AAPL", "policy_id": subject.POLICY_ID,
                "paper_decision": "BUY_CANDIDATE", "technical_context_score": 0.2,
                "locked_score_cutoff": 0.15986412677273237,
            }],
        }
        value.update(changes)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_complete_payload_emits_paper_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            self.payload(path)
            rows = subject.scan([{"symbol": "AAPL", "price": 200}], {
                "nasdaq100_daily_payload_path": str(path),
            })
            self.assertEqual(rows[0]["decision"], "BUY_CANDIDATE")
            self.assertEqual(rows[0]["requested_position_dollars"], 200)

    def test_live_enabled_payload_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            self.payload(path, live_trading_enabled=True)
            rows = subject.scan([{"symbol": "AAPL", "price": 200}], {
                "nasdaq100_daily_payload_path": str(path),
            })
            self.assertEqual(rows[0]["decision"], "AVOID")

    def test_below_locked_cutoff_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            self.payload(path, candidates=[{
                "symbol": "AAPL", "policy_id": subject.POLICY_ID,
                "paper_decision": "BUY_CANDIDATE", "technical_context_score": 0.1,
                "locked_score_cutoff": 0.15986412677273237,
            }])
            rows = subject.scan([{"symbol": "AAPL", "price": 200}], {
                "nasdaq100_daily_payload_path": str(path),
            })
            self.assertEqual(rows[0]["decision"], "AVOID")

    def test_symbol_outside_training_universe_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            self.payload(path, candidates=[{
                "symbol": "UNSEEN", "policy_id": subject.POLICY_ID,
                "paper_decision": "BUY_CANDIDATE", "technical_context_score": 0.9,
                "locked_score_cutoff": 0.15986412677273237,
            }])
            rows = subject.scan([{"symbol": "UNSEEN", "price": 200}], {
                "nasdaq100_daily_payload_path": str(path),
            })
            self.assertEqual(rows[0]["decision"], "AVOID")


if __name__ == "__main__":
    unittest.main()
