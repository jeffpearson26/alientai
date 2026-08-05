from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

from compile_rolling_twenty_minute_panel import (
    build_training_frame,
    compile_archive,
    feature_names,
)


def session(multiplier: float = 1.0) -> pd.DataFrame:
    start = datetime(2026, 7, 31, 9, 30)
    rows = []
    for index in range(390):
        price = multiplier * (100.0 + index * 0.01)
        rows.append(
            {
                "timestamp": start + timedelta(minutes=index),
                "open": price - 0.01,
                "high": price + 0.02,
                "low": price - 0.02,
                "close": price,
                "volume": 1000 + index,
            }
        )
    return pd.DataFrame(rows)


class CompileRollingTwentyMinutePanelTests(unittest.TestCase):
    def _write_archive(
        self,
        raw_root: Path,
        status: str,
        include_spy: bool = True,
        target_symbol: str = "AAA",
    ) -> None:
        records = []
        inputs = [(target_symbol, 1.0), ("QQQ", 1.1)]
        if include_spy:
            inputs.append(("SPY", 0.9))
        for symbol, multiplier in inputs:
            path = raw_root / "2026" / "2026-07" / f"{symbol}.csv.gz"
            path.parent.mkdir(parents=True, exist_ok=True)
            content = session(multiplier).to_csv(index=False).encode()
            with gzip.open(path, "wb") as handle:
                handle.write(content)
            records.append(
                {
                    "symbol": symbol,
                    "month": "2026-07",
                    "relative_path": path.relative_to(raw_root).as_posix(),
                    "content_sha256": hashlib.sha256(content).hexdigest(),
                }
            )
        (raw_root / "manifest.json").write_text(
            json.dumps(
                {
                    "status": status,
                    "failed": [],
                    "unavailable": [],
                    "start_month": "2026-07",
                    "end_month": "2026-07",
                    "function": "TIME_SERIES_INTRADAY",
                    "interval": "1min",
                    "adjusted": True,
                    "extended_hours": True,
                    "timestamp_convention": "interval_start",
                    "timestamp_timezone": "America/New_York",
                    "completed": records,
                }
            ),
            encoding="utf-8",
        )

    def test_compiler_resumes_matching_shards_without_rewriting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_root = root / "raw"
            output_root = root / "compiled"
            self._write_archive(raw_root, status="complete")
            first = compile_archive(raw_root, output_root, ["AAA"])
            shard = output_root / first["completed"][0]["relative_path"]
            self.assertEqual(first["timestamp_unit"], "ns_since_unix_epoch")
            self.assertEqual(first["schema_version"], 3)
            self.assertEqual(first["entry_assumption"], "next_minute_open")
            with np.load(shard) as values:
                first_timestamp = values["timestamp"][0].astype("datetime64[ns]")
                first_entry = values["entry_timestamp"][0].astype("datetime64[ns]")
            self.assertEqual(
                first_timestamp,
                np.datetime64("2026-07-31T09:30:00", "ns"),
            )
            self.assertEqual(
                first_entry,
                np.datetime64("2026-07-31T09:31:00", "ns"),
            )
            modified = shard.stat().st_mtime_ns
            second = compile_archive(raw_root, output_root, ["AAA"])
            self.assertEqual(second["status"], "complete")
            self.assertEqual(shard.stat().st_mtime_ns, modified)

    def test_running_archive_requires_explicit_snapshot_flag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_root = root / "raw"
            self._write_archive(raw_root, status="running")
            with self.assertRaisesRegex(ValueError, "explicitly compiled"):
                compile_archive(raw_root, root / "compiled", ["AAA"])

    def test_running_snapshot_is_permanently_labeled_partial(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_root = root / "raw"
            self._write_archive(raw_root, status="running")
            result = compile_archive(
                raw_root,
                root / "compiled",
                ["AAA"],
                allow_running_snapshot=True,
            )
            self.assertEqual(result["status"], "complete")
            self.assertTrue(result["partial_snapshot"])
            self.assertEqual(result["source_snapshot"]["compiled_months"], ["2026-07"])

    def test_running_snapshot_skips_month_without_benchmark_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_root = root / "raw"
            self._write_archive(raw_root, status="running", include_spy=False)
            with self.assertRaisesRegex(ValueError, "no source months"):
                compile_archive(
                    raw_root,
                    root / "compiled",
                    ["AAA"],
                    allow_running_snapshot=True,
                )

    def test_full_session_produces_every_valid_twenty_minute_start(self) -> None:
        frame = build_training_frame(session(), session(1.1), session(0.9))
        self.assertEqual(len(frame), 370)
        self.assertEqual(frame.iloc[0]["timestamp"].strftime("%H:%M"), "09:30")
        self.assertEqual(
            frame.iloc[-1]["target_timestamp"].strftime("%H:%M"),
            "16:00",
        )
        self.assertEqual(frame.iloc[0]["entry_timestamp"].strftime("%H:%M"), "09:31")

    def test_configurable_five_minute_horizon_uses_next_minute_open(self) -> None:
        symbol = session()
        frame = build_training_frame(
            symbol,
            session(1.1),
            session(0.9),
            horizon_minutes=5,
        )
        self.assertEqual(len(frame), 385)
        first = frame.iloc[0]
        expected = (symbol.iloc[5]["close"] / symbol.iloc[1]["open"] - 1.0) * 100.0
        self.assertAlmostEqual(first["forward_return_gross_pct"], expected)
        self.assertEqual(first["entry_timestamp"].strftime("%H:%M"), "09:31")
        self.assertEqual(first["target_bar_start_timestamp"].strftime("%H:%M"), "09:35")
        self.assertEqual(first["target_timestamp"].strftime("%H:%M"), "09:36")

    def test_horizon_contract_prevents_output_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_root = root / "raw"
            output_root = root / "compiled"
            self._write_archive(raw_root, status="complete")
            compile_archive(
                raw_root,
                output_root,
                ["AAA"],
                horizon_minutes=5,
            )
            with self.assertRaisesRegex(ValueError, "contract mismatch"):
                compile_archive(
                    raw_root,
                    output_root,
                    ["AAA"],
                    horizon_minutes=10,
                )

    def test_compiler_combines_main_and_supplemental_archives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            main = root / "main"
            supplemental = root / "supplemental"
            self._write_archive(main, status="complete", target_symbol="AAA")
            self._write_archive(
                supplemental,
                status="complete",
                target_symbol="BBB",
            )
            result = compile_archive(
                main,
                root / "compiled",
                ["AAA", "BBB"],
                horizon_minutes=5,
                supplemental_raw_roots=[supplemental],
            )
            symbols = {item["symbol"] for item in result["completed"]}
            self.assertEqual(symbols, {"AAA", "BBB"})
            self.assertEqual(result["source_snapshot"]["source_archive_count"], 2)
            self.assertEqual(result["target_symbols"], ["AAA", "BBB"])
            self.assertEqual(result["target_symbols_count"], 2)

    def test_complete_archive_requires_every_symbol_month_accounted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_root = root / "raw"
            self._write_archive(raw_root, status="complete")
            manifest_path = raw_root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["start_month"] = "2026-06"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "do not account"):
                compile_archive(raw_root, root / "compiled", ["AAA"])

    def test_combined_archives_reject_conflicting_benchmark_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            main = root / "main"
            supplemental = root / "supplemental"
            self._write_archive(main, status="complete", target_symbol="AAA")
            self._write_archive(
                supplemental,
                status="complete",
                target_symbol="BBB",
            )
            manifest_path = supplemental / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            qqq = next(
                record
                for record in manifest["completed"]
                if record["symbol"] == "QQQ"
            )
            qqq["content_sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
                compile_archive(
                    main,
                    root / "compiled",
                    ["AAA", "BBB"],
                    supplemental_raw_roots=[supplemental],
                )

    def test_missing_future_minute_removes_crossing_targets(self) -> None:
        symbol = session()
        missing_stamp = datetime(2026, 7, 31, 10, 10)
        symbol = symbol[symbol["timestamp"] != missing_stamp]
        frame = build_training_frame(symbol, session(1.1), session(0.9))
        crossing = frame[
            (frame["timestamp"] < missing_stamp)
            & (frame["target_bar_start_timestamp"] >= missing_stamp)
        ]
        self.assertTrue(crossing.empty)
        after_gap = frame[
            frame["timestamp"] == missing_stamp + timedelta(minutes=1)
        ].iloc[0]
        self.assertEqual(after_gap["history_1m_available"], 0.0)
        self.assertTrue(pd.isna(after_gap["return_1m_pct"]))
        self.assertTrue(pd.isna(after_gap["realized_volatility_20m_pct"]))

    def test_features_exclude_all_targets_and_future_prices(self) -> None:
        names = feature_names()
        self.assertTrue(names)
        self.assertFalse(any("target" in name or "forward" in name for name in names))
        frame = build_training_frame(session(), session(1.1), session(0.9))
        self.assertTrue(set(names).issubset(frame.columns))

    def test_market_context_requires_exact_timestamp(self) -> None:
        qqq = session(1.1)
        qqq = qqq[qqq["timestamp"] != datetime(2026, 7, 31, 10, 0)]
        frame = build_training_frame(session(), qqq, session(0.9))
        self.assertNotIn(
            datetime(2026, 7, 31, 10, 0),
            set(frame["timestamp"]),
        )


if __name__ == "__main__":
    unittest.main()
