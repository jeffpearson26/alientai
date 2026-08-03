from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from audit_intraday_prospective_readiness import build_audit


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


class IntradayReadinessAuditTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> dict:
        symbols_path = root / "symbols.txt"
        symbols_path.write_text("AAA\nBBB\n", encoding="utf-8")
        technical = root / "technical.jsonl"
        calls = root / "calls.jsonl"
        events = root / "events.jsonl"
        write_jsonl(
            technical,
            [
                {"symbol": symbol, "market_date": "2026-07-31"}
                for symbol in ("AAA", "BBB")
            ],
        )
        write_jsonl(
            calls,
            [
                {"symbol": symbol, "market_date": "2026-07-31"}
                for symbol in ("AAA", "BBB")
            ],
        )
        write_jsonl(
            events,
            [
                {
                    "symbol": symbol,
                    "market_date": "2026-08-03",
                    "as_of_utc": "2026-08-03T13:25:00+00:00",
                }
                for symbol in ("AAA", "BBB")
            ],
        )
        for name in (
            "ai_semiconductor_20min_technical",
            "ai_semiconductor_20min_premarket",
            "ai_semiconductor_20min_calls",
            "ai_semiconductor_60min_technical",
            "ai_semiconductor_60min_premarket",
            "ai_semiconductor_60min_calls",
        ):
            directory = root / name
            directory.mkdir()
            (directory / "natural_technical_context_classifier.txt").write_text(
                name, encoding="utf-8"
            )
            (directory / "natural_technical_context_report.json").write_text(
                json.dumps(
                    {
                        "research_only": True,
                        "execution_enabled": False,
                        "target": "return",
                    }
                ),
                encoding="utf-8",
            )
        return {
            "technical_path": technical,
            "call_history_path": calls,
            "events_path": events,
            "model_root": root,
            "symbols_path": symbols_path,
            "decision_date": "2026-08-03",
            "prior_session_date": "2026-07-31",
            "generated_at": datetime(2026, 8, 3, tzinfo=timezone.utc),
        }

    def test_records_exact_inputs_and_frozen_models(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            audit = build_audit(**self.make_fixture(Path(directory)))
        self.assertEqual(audit["status"], "ready_for_exact_0925_collection")
        self.assertEqual(audit["universe_size"], 2)
        self.assertEqual(len(audit["models"]), 6)
        self.assertFalse(audit["execution_enabled"])

    def test_rejects_partial_panel(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.make_fixture(Path(directory))
            write_jsonl(
                fixture["technical_path"],
                [{"symbol": "AAA", "market_date": "2026-07-31"}],
            )
            with self.assertRaisesRegex(ValueError, "exact frozen universe"):
                build_audit(**fixture)

    def test_rejects_wrong_cutoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.make_fixture(Path(directory))
            write_jsonl(
                fixture["events_path"],
                [
                    {
                        "symbol": symbol,
                        "market_date": "2026-08-03",
                        "as_of_utc": "2026-08-03T13:20:00+00:00",
                    }
                    for symbol in ("AAA", "BBB")
                ],
            )
            with self.assertRaisesRegex(ValueError, "exactly 09:25"):
                build_audit(**fixture)

    def test_rejects_execution_enabled_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.make_fixture(Path(directory))
            report = (
                fixture["model_root"]
                / "ai_semiconductor_20min_calls"
                / "natural_technical_context_report.json"
            )
            payload = json.loads(report.read_text(encoding="utf-8"))
            payload["execution_enabled"] = True
            report.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fail closed"):
                build_audit(**fixture)


if __name__ == "__main__":
    unittest.main()
