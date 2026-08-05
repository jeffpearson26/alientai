import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from capture_schwab_intraday_snapshot import capture
from evaluate_schwab_late_intraday_outcomes import completed_outcomes
from download_russell_2000_5m_schwab import read_symbols as read_schwab_symbols
from journal_ai_semiconductor_late_intraday_models import (
    merge_inputs,
    validate_capture_window,
)


class SchwabLateIntradayProgramTests(unittest.TestCase):
    def test_schwab_symbol_reader_ignores_documentation_comments(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "symbols.txt"
            path.write_text("# research basket\nNVDA\nAMD\n", encoding="utf-8")
            self.assertEqual(read_schwab_symbols(path), ["NVDA", "AMD"])

    def write_archive(self, root: Path, captured_at: str) -> None:
        rows = [
            ("2026-08-03T20:00:00+00:00", 100, 100),
            ("2026-08-04T13:25:00+00:00", 101, 102),
        ]
        for minute in range(35, 60, 5):
            rows.append((f"2026-08-04T13:{minute:02d}:00+00:00", 102, 103))
        for minute in range(0, 35, 5):
            rows.append((f"2026-08-04T14:{minute:02d}:00+00:00", 103, 106))
        path = root / "NVDA_schwab_5m_max.csv"
        lines = ["symbol,datetime_ms,datetime_utc,open,high,low,close,volume"]
        lines.extend(
            f"NVDA,{index},{stamp},{open_},{close_},{open_},{close_},100"
            for index, (stamp, open_, close_) in enumerate(rows, 1)
        )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        (root / "manifest.json").write_text(json.dumps({
            "status": "complete",
            "source": "Schwab pricehistory",
            "mode": "current",
            "bar_interval_minutes": 5,
            "timestamp_convention": "interval_start",
            "decision_date": "2026-08-04",
            "captured_at_utc": captured_at,
        }), encoding="utf-8")

    def test_capture_window_accepts_only_preentry_snapshot(self):
        manifest = {
            "status": "complete",
            "source": "Schwab pricehistory",
            "mode": "current",
            "bar_interval_minutes": 5,
            "timestamp_convention": "interval_start",
            "decision_date": "2026-08-04",
            "captured_at_utc": "2026-08-04T13:31:00+00:00",
        }
        validate_capture_window(
            "2026-08-04",
            manifest,
            datetime(2026, 8, 4, 13, 32, tzinfo=timezone.utc),
        )
        with self.assertRaises(ValueError):
            validate_capture_window(
                "2026-08-04",
                manifest,
                datetime(2026, 8, 4, 13, 36, tzinfo=timezone.utc),
            )

    def test_outcome_capture_mode_accepts_only_at_or_after_1035(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "before 10:35"):
                capture(
                    [],
                    "2026-08-04",
                    root / "too_early",
                    datetime(2026, 8, 4, 14, 34, tzinfo=timezone.utc),
                    purpose="outcome",
                )
            manifest = capture(
                [],
                "2026-08-04",
                root / "complete",
                datetime(2026, 8, 4, 14, 35, tzinfo=timezone.utc),
                purpose="outcome",
            )
        self.assertEqual(manifest["purpose"], "outcome")

    def test_merge_uses_exact_schwab_0925_premarket(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_archive(root, "2026-08-04T13:31:00+00:00")
            rows = merge_inputs(
                [{"symbol": "NVDA", "market_date": "2026-08-03", "technical_rsi_2": 4}],
                [{"symbol": "NVDA", "market_date": "2026-08-03", "call_volume_unusual": True}],
                root,
                "2026-08-04",
                "2026-08-03",
                ["NVDA"],
            )
        self.assertEqual(rows[0]["model_premarket_last_timestamp_et"], "2026-08-04 09:25:00")
        self.assertEqual(rows[0]["prior_feature_market_date"], "2026-08-03")
        self.assertTrue(rows[0]["model_call_volume_unusual"])

    def test_merge_rejects_stale_prior_features(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_archive(root, "2026-08-04T13:31:00+00:00")
            with self.assertRaisesRegex(ValueError, "stale"):
                merge_inputs(
                    [{"symbol": "NVDA", "market_date": "2026-07-31"}],
                    [{"symbol": "NVDA", "market_date": "2026-07-31"}],
                    root,
                    "2026-08-04",
                    "2026-08-03",
                    ["NVDA"],
                )

    def test_outcome_uses_0935_open_and_1030_close(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_archive(root, "2026-08-04T14:36:00+00:00")
            outcomes = completed_outcomes(
                [{
                    "model_id": "late",
                    "model_sha256": "abc",
                    "market_date": "2026-08-04",
                    "symbol": "NVDA",
                    "rank": 1,
                    "model_score": 0.8,
                    "horizon_minutes": 60,
                }],
                root,
                datetime(2026, 8, 4, 14, 36, tzinfo=timezone.utc),
            )
        self.assertEqual(outcomes[0]["label_entry_0935_open"], 102)
        self.assertEqual(outcomes[0]["label_exit_1030_close"], 106)


if __name__ == "__main__":
    unittest.main()
