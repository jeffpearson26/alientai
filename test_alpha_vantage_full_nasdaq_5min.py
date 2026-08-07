from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from audit_alpha_vantage_full_nasdaq_5min import (
    audit,
    validate_normalized_content,
)
from download_alpha_vantage_full_nasdaq_5min import (
    NORMALIZED_FIELDS,
    append_ledger,
    normalize_provider_csv,
    provider_blackout_remaining_seconds,
    read_latest_ledger,
    request_key,
    run,
    series_relative_path,
    validate_final_states,
)


PACIFIC = ZoneInfo("America/Los_Angeles")


class FullNasdaqFiveMinuteTests(unittest.TestCase):
    def test_normalizes_ohlcv_without_fabricating_optional_fields(self) -> None:
        source = (
            "timestamp,open,high,low,close,volume\n"
            "2026-07-02 09:35:00,10,12,9,11,100\n"
            "2026-07-02 09:30:00,9,11,8,10,90\n"
        ).encode()
        content, details = normalize_provider_csv(
            source,
            symbol="TEST",
            month="2026-07",
        )
        text = content.decode()
        self.assertEqual(details["rows"], 2)
        self.assertEqual(details["vwap_rows"], 0)
        self.assertEqual(details["number_of_trades_rows"], 0)
        self.assertIn(
            ",".join(NORMALIZED_FIELDS),
            text.splitlines()[0],
        )
        self.assertIn(",TEST,9,11,8,10,90,,,false,false", text)
        audited = validate_normalized_content(
            content,
            symbol="TEST",
            month="2026-07",
        )
        self.assertEqual(audited["first_timestamp_et"], "2026-07-02 09:30:00")

    def test_preserves_optional_fields_only_when_present(self) -> None:
        source = (
            "timestamp,open,high,low,close,volume,vwap,transactions\n"
            "2026-07-02 09:30:00,9,11,8,10,90,9.75,12\n"
        ).encode()
        content, details = normalize_provider_csv(
            source,
            symbol="TEST",
            month="2026-07",
        )
        self.assertEqual(details["vwap_rows"], 1)
        self.assertEqual(details["number_of_trades_rows"], 1)
        self.assertIn(",9.75,12,true,true", content.decode())

    def test_ledger_latest_record_wins(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ledger.jsonl"
            key = request_key("TEST", "2026-07")
            append_ledger(path, {"request": key, "state": "failed"})
            append_ledger(path, {"request": key, "state": "completed"})
            self.assertEqual(read_latest_ledger(path)[key]["state"], "completed")

    def test_hashed_relative_paths_are_distinct(self) -> None:
        first = series_relative_path("A/B", "2026-07")
        second = series_relative_path("AB", "2026-07")
        self.assertNotEqual(first, second)
        self.assertEqual(first.parts[:2], ("2026", "2026-07"))

    def test_weekday_blackout_and_weekend_allowance(self) -> None:
        weekday = datetime(2026, 8, 7, 5, 0, tzinfo=PACIFIC)
        weekend = datetime(2026, 8, 8, 5, 0, tzinfo=PACIFIC)
        self.assertEqual(
            provider_blackout_remaining_seconds(weekday),
            110 * 60,
        )
        self.assertEqual(provider_blackout_remaining_seconds(weekend), 0)

    def test_normalized_gzip_round_trip(self) -> None:
        source = (
            "timestamp,open,high,low,close,volume\n"
            "2026-07-02 09:30:00,9,11,8,10,90\n"
        ).encode()
        content, _ = normalize_provider_csv(
            source,
            symbol="TEST",
            month="2026-07",
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sample.csv.gz"
            with gzip.open(path, "wb") as handle:
                handle.write(content)
            with gzip.open(path, "rb") as handle:
                decoded = handle.read()
        self.assertEqual(decoded, content)

    def test_rejects_corrupted_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ledger.jsonl"
            path.write_text(json.dumps({"state": "completed"}) + "\n")
            with self.assertRaises(ValueError):
                read_latest_ledger(path)

    def test_rejects_out_of_contract_final_state(self) -> None:
        with self.assertRaises(ValueError):
            validate_final_states(
                {
                    "OTHER|2026-07": {
                        "request": "OTHER|2026-07",
                        "state": "completed",
                    }
                },
                symbols=["TEST"],
                months=["2026-07"],
            )

    def test_seed_only_archive_runs_and_audits_without_network(self) -> None:
        temp_root = Path("D:/AlientAI/Temp")
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as temporary:
            root = Path(temporary)
            universe = root / "universe.json"
            universe.write_text(
                json.dumps(
                    {
                        "rows": [
                            {
                                "symbol": "TEST",
                                "name": "Test",
                                "exchange": "NASDAQ",
                                "asset_type": "Stock",
                                "ipo_date": "2020-01-01",
                                "status": "Active",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            seed = root / "seed"
            seed_path = seed / "2026" / "2026-07" / "TEST.csv.gz"
            seed_path.parent.mkdir(parents=True)
            raw = (
                "timestamp,open,high,low,close,volume\n"
                "2026-07-02 09:30:00,9,11,8,10,90\n"
            ).encode()
            with gzip.open(seed_path, "wb") as handle:
                handle.write(raw)
            (seed / "manifest.json").write_text(
                json.dumps(
                    {
                        "status": "complete",
                        "source": "alpha_vantage",
                        "function": "TIME_SERIES_INTRADAY",
                        "interval": "5min",
                        "adjusted": True,
                        "extended_hours": True,
                        "completed": [
                            {
                                "request": "TEST|2026-07",
                                "relative_path": "2026/2026-07/TEST.csv.gz",
                            }
                        ],
                        "unavailable": [],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "output"
            result = run(
                universe_path=universe,
                output=output,
                start_month="2026-07",
                end_month="2026-07",
                api_key="not-used",
                delay_seconds=0,
                minimum_free_gib=0,
                retries=1,
                retry_wait_seconds=0,
                seed_archive=seed,
            )
            self.assertEqual(result["status"], "complete")
            report = audit(output, universe)
            self.assertTrue(report["integrity_pass"])
            self.assertEqual(report["completed_count"], 1)
            self.assertEqual(report["total_rows"], 1)


if __name__ == "__main__":
    unittest.main()
