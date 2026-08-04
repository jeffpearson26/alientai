from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

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
    def test_compiler_resumes_matching_shards_without_rewriting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_root = root / "raw"
            output_root = root / "compiled"
            records = []
            for symbol, multiplier in (("AAA", 1.0), ("QQQ", 1.1), ("SPY", 0.9)):
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
                        "status": "complete",
                        "failed": [],
                        "interval": "1min",
                        "completed": records,
                    }
                ),
                encoding="utf-8",
            )
            first = compile_archive(raw_root, output_root, ["AAA"])
            shard = output_root / first["completed"][0]["relative_path"]
            modified = shard.stat().st_mtime_ns
            second = compile_archive(raw_root, output_root, ["AAA"])
            self.assertEqual(second["status"], "complete")
            self.assertEqual(shard.stat().st_mtime_ns, modified)

    def test_full_session_produces_every_valid_twenty_minute_start(self) -> None:
        frame = build_training_frame(session(), session(1.1), session(0.9))
        self.assertEqual(len(frame), 370)
        self.assertEqual(frame.iloc[0]["timestamp"].strftime("%H:%M"), "09:30")
        self.assertEqual(
            frame.iloc[-1]["target_timestamp"].strftime("%H:%M"),
            "15:59",
        )

    def test_missing_future_minute_removes_crossing_targets(self) -> None:
        symbol = session()
        missing_stamp = datetime(2026, 7, 31, 10, 10)
        symbol = symbol[symbol["timestamp"] != missing_stamp]
        frame = build_training_frame(symbol, session(1.1), session(0.9))
        crossing = frame[
            (frame["timestamp"] < missing_stamp)
            & (frame["target_timestamp"] >= missing_stamp)
        ]
        self.assertTrue(crossing.empty)

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
