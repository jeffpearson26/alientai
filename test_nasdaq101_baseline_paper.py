import json
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from alientai_v2.engines import nasdaq101_baseline_paper as subject


class Nasdaq101BaselinePaperTests(unittest.TestCase):
    def payload(self, path: Path, **changes):
        today = datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()
        symbols = sorted(subject._canonical_symbols())
        value = {
            "status": "paper_payload_ready",
            "research_only": True,
            "paper_only": True,
            "live_trading_enabled": False,
            "policy_id": subject.POLICY_ID,
            "source": "schwab_daily_history",
            "source_pure": True,
            "market_date": today,
            "market_session_date": today,
            "universe_rows": 101,
            "training_universe_size": 101,
            "training_universe_symbols": symbols,
            "symbols_sha256": subject.EXPECTED_SYMBOLS_SHA256,
            "model_sha256": subject.EXPECTED_MODEL_SHA256,
            "training_report_sha256": subject.EXPECTED_REPORT_SHA256,
            "locked_score_cutoff": subject.LOCKED_SCORE_CUTOFF,
            "candidates": [{
                "symbol": symbols[0],
                "policy_id": subject.POLICY_ID,
                "paper_decision": "BUY_CANDIDATE",
                "model_score": subject.LOCKED_SCORE_CUTOFF + 0.01,
                "locked_score_cutoff": subject.LOCKED_SCORE_CUTOFF,
                "confidence_rank_1_to_100": 100,
            }],
        }
        value.update(changes)
        path.write_text(json.dumps(value), encoding="utf-8")
        return symbols[0]

    def settings(self, path: Path):
        return {
            "nasdaq101_baseline_paper_enabled": True,
            "nasdaq101_baseline_paper_payload_path": str(path),
        }

    def test_complete_payload_emits_one_share_paper_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            symbol = self.payload(path)
            rows = subject.scan(
                [{"symbol": symbol, "price": 200.0}], self.settings(path)
            )
            self.assertEqual(rows[0]["decision"], "BUY_CANDIDATE")
            self.assertEqual(rows[0]["engine_id"], subject.POLICY_ID)
            self.assertEqual(rows[0]["requested_position_dollars"], 200.0)
            self.assertTrue(rows[0]["paper_only"])
            self.assertFalse(rows[0]["live_trading_enabled"])

    def test_disabled_setting_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            symbol = self.payload(path)
            rows = subject.scan([{"symbol": symbol, "price": 200.0}], {
                "nasdaq101_baseline_paper_payload_path": str(path),
            })
            self.assertEqual(rows[0]["decision"], "AVOID")

    def test_incomplete_universe_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            symbol = self.payload(path, universe_rows=100)
            rows = subject.scan(
                [{"symbol": symbol, "price": 200.0}], self.settings(path)
            )
            self.assertEqual(rows[0]["decision"], "AVOID")

    def test_wrong_model_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            symbol = self.payload(path, model_sha256="0" * 64)
            rows = subject.scan(
                [{"symbol": symbol, "price": 200.0}], self.settings(path)
            )
            self.assertEqual(rows[0]["decision"], "AVOID")

    def test_live_enabled_payload_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            symbol = self.payload(path, live_trading_enabled=True)
            rows = subject.scan(
                [{"symbol": symbol, "price": 200.0}], self.settings(path)
            )
            self.assertEqual(rows[0]["decision"], "AVOID")

    def test_open_position_add_requires_five_minute_uptrend(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload_path = root / "payload.json"
            state_path = root / "state.json"
            account_path = root / "account.json"
            symbol = self.payload(payload_path)
            state_path.write_text(json.dumps({
                "samples": {
                    symbol: [{
                        "observed_at_epoch": time.time() - 301,
                        "price": 100.0,
                    }],
                },
            }), encoding="utf-8")
            account_path.write_text(json.dumps({
                "open_positions": {
                    symbol: {
                        "engine_id": subject.POLICY_ID,
                        "entry_price": 100.0,
                        "risk_entry_price": 100.0,
                        "last_add_epoch": time.time() - 301,
                    },
                },
            }), encoding="utf-8")
            settings = self.settings(payload_path)
            settings.update({
                "nasdaq101_baseline_trend_state_path": str(state_path),
                "nasdaq101_baseline_paper_account_path": str(account_path),
                "nasdaq101_baseline_pyramid_enabled": True,
            })
            rows = subject.scan([{"symbol": symbol, "price": 101.0}], settings)
            self.assertEqual(rows[0]["decision"], "BUY_CANDIDATE")
            self.assertTrue(rows[0]["paper_pyramid_allowed"])
            self.assertEqual(rows[0]["paper_pyramid_shares"], 1)


if __name__ == "__main__":
    unittest.main()
