import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from audit_schwab_late_entry_readiness import build_readiness


class LateEntryReadinessTests(unittest.TestCase):
    def fixture(self, root: Path, call_history: int = 10, date: str = "2026-08-03"):
        symbols = root / "symbols.txt"
        symbols.write_text("AMD\nNVDA\n", encoding="utf-8")
        technical = root / "technical.jsonl"
        calls = root / "calls.jsonl"
        manifest = root / "manifest.json"
        technical.write_text("".join(
            json.dumps({"symbol": symbol, "market_date": date,
                        "source": "alpha_vantage_time_series_daily"}) + "\n"
            for symbol in ("AMD", "NVDA")
        ), encoding="utf-8")
        calls.write_text("".join(
            json.dumps({"symbol": symbol, "market_date": date,
                        "call_activity_history_count": call_history}) + "\n"
            for symbol in ("AMD", "NVDA")
        ), encoding="utf-8")
        manifest.write_text(json.dumps({
            "status": "frozen", "research_only": True,
            "execution_enabled": False, "universe_size": 2,
        }), encoding="utf-8")
        return technical, calls, symbols, manifest

    def test_exact_ready_inputs_pass(self):
        with TemporaryDirectory() as directory:
            paths = self.fixture(Path(directory))
            result = build_readiness(
                *paths, "2026-08-04", "2026-08-03"
            )
        self.assertEqual(result["status"], "READY")

    def test_stale_date_fails(self):
        with TemporaryDirectory() as directory:
            paths = self.fixture(Path(directory), date="2026-07-31")
            with self.assertRaisesRegex(ValueError, "stale"):
                build_readiness(*paths, "2026-08-04", "2026-08-03")

    def test_insufficient_call_history_fails(self):
        with TemporaryDirectory() as directory:
            paths = self.fixture(Path(directory), call_history=9)
            with self.assertRaisesRegex(ValueError, "minimum history"):
                build_readiness(*paths, "2026-08-04", "2026-08-03")


if __name__ == "__main__":
    unittest.main()
