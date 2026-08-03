from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from build_claude_competition_packet import build_packet


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


class ClaudeCompetitionPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.universe = self.root / "universe.txt"
        self.universe.write_text("# comment\nAAA\nBBB\n", encoding="utf-8")
        self.technical = self.root / "technical.jsonl"
        write_jsonl(
            self.technical,
            [
                {
                    "symbol": "AAA",
                    "market_date": "2026-07-31",
                    "close": 10.0,
                    "technical_rsi_14": 45.0,
                    "model_score": 0.99,
                    "future_return_5d": 20.0,
                },
                {
                    "symbol": "BBB",
                    "market_date": "2026-07-31",
                    "close": 20.0,
                    "technical_rsi_14": 55.0,
                },
            ],
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def build(self, **kwargs):
        return build_packet(
            decision_date_text="2026-08-03",
            universe_file=self.universe,
            technical_panel=self.technical,
            output_dir=self.root / "out",
            generated_at=datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
            **kwargs,
        )

    def test_builds_single_uploadable_zip_and_excludes_model_outputs(self) -> None:
        outputs = self.build()
        payload = json.loads(outputs["json"].read_text(encoding="utf-8"))
        self.assertEqual(payload["manifest"]["universe_size"], 2)
        self.assertEqual(
            payload["manifest"]["included_feature_families"],
            ["prior_close_technical"],
        )
        first = payload["records"][0]["technical"]
        self.assertNotIn("model_score", first)
        self.assertNotIn("future_return_5d", first)
        with zipfile.ZipFile(outputs["zip"]) as archive:
            self.assertEqual(
                sorted(archive.namelist()),
                ["README.md", "claude_competition_data.json"],
            )

    def test_rejects_partial_universe(self) -> None:
        write_jsonl(
            self.technical,
            [
                {
                    "symbol": "AAA",
                    "market_date": "2026-07-31",
                    "close": 10.0,
                }
            ],
        )
        with self.assertRaisesRegex(ValueError, "coverage mismatch"):
            self.build()

    def test_rejects_same_day_technical_features(self) -> None:
        rows = [
            {"symbol": symbol, "market_date": "2026-08-03", "close": 10.0}
            for symbol in ("AAA", "BBB")
        ]
        write_jsonl(self.technical, rows)
        with self.assertRaisesRegex(ValueError, "must precede"):
            self.build()

    def test_accepts_only_exact_complete_0925_premarket_panel(self) -> None:
        premarket = self.root / "premarket.jsonl"
        write_jsonl(
            premarket,
            [
                {
                    "symbol": symbol,
                    "market_date": "2026-08-03",
                    "premarket_available": True,
                    "premarket_cutoff_et": "09:25",
                    "premarket_last_timestamp_et": "2026-08-03 09:25:00",
                    "premarket_gap_pct": value,
                }
                for symbol, value in (("AAA", 1.0), ("BBB", -1.0))
            ],
        )
        outputs = self.build(premarket_panel=premarket)
        payload = json.loads(outputs["json"].read_text(encoding="utf-8"))
        self.assertIn(
            "current_premarket_through_09_25_et",
            payload["manifest"]["included_feature_families"],
        )

        rows = [
            json.loads(line)
            for line in premarket.read_text(encoding="utf-8").splitlines()
        ]
        rows[0]["premarket_last_timestamp_et"] = "2026-08-03 09:20:00"
        write_jsonl(premarket, rows)
        with self.assertRaisesRegex(ValueError, "exactly at 09:25"):
            self.build(premarket_panel=premarket)

    def test_rejects_call_features_from_wrong_session(self) -> None:
        calls = self.root / "calls.jsonl"
        write_jsonl(
            calls,
            [
                {
                    "symbol": symbol,
                    "market_date": "2026-07-30",
                    "call_volume_unusual": False,
                }
                for symbol in ("AAA", "BBB")
            ],
        )
        with self.assertRaisesRegex(ValueError, "prior technical session"):
            self.build(call_panel=calls)


if __name__ == "__main__":
    unittest.main()
