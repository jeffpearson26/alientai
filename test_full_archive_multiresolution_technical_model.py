from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from alientai_v2.research.multiresolution_cross_sectional import (
    FIVE_MINUTE_FEATURES,
)
from build_full_archive_multiresolution_technical_panel import (
    _adjusted_daily_rows,
    build_rows,
    read_symbols,
    split_dates,
)
from complete_full_archive_multiresolution_technical_model import (
    conflicting_model_jobs,
)


class FakeProcess:
    def __init__(self, pid: int, name: str, command: list[str]) -> None:
        self.info = {
            "pid": pid,
            "name": name,
            "cmdline": command,
        }


class FullArchiveMultiresolutionTechnicalTests(unittest.TestCase):
    def test_capacity_detection_ignores_non_python_monitor_text(self) -> None:
        processes = [
            FakeProcess(
                1001,
                "powershell.exe",
                [
                    "powershell.exe",
                    "-Command",
                    "inspect train_full_archive_multiresolution_technical.py",
                ],
            ),
            FakeProcess(
                1002,
                "python.exe",
                [
                    "python.exe",
                    "compile_rolling_twenty_minute_panel.py",
                ],
            ),
            FakeProcess(
                os.getpid(),
                "python.exe",
                [
                    "python.exe",
                    "train_full_archive_multiresolution_technical.py",
                ],
            ),
        ]
        with patch(
            "complete_full_archive_multiresolution_technical_model."
            "psutil.process_iter",
            return_value=processes,
        ):
            actual = conflicting_model_jobs()

        self.assertEqual(1, len(actual))
        self.assertEqual(1002, actual[0]["pid"])

    def test_daily_adjustment_keeps_raw_volume(self) -> None:
        payload = {
            "Time Series (Daily)": {
                f"2026-01-{day:02d}": {
                    "1. open": "100",
                    "2. high": "110",
                    "3. low": "90",
                    "4. close": "100",
                    "5. adjusted close": "50",
                    "6. volume": "1234",
                    "7. dividend amount": "0",
                    "8. split coefficient": "1",
                }
                for day in range(1, 29)
            }
            | {
                f"2025-12-{day:02d}": {
                    "1. open": "100",
                    "2. high": "110",
                    "3. low": "90",
                    "4. close": "100",
                    "5. adjusted close": "50",
                    "6. volume": "1234",
                    "7. dividend amount": "0",
                    "8. split coefficient": "1",
                }
                for day in range(1, 32)
            }
            | {
                "2025-11-30": {
                    "1. open": "100",
                    "2. high": "110",
                    "3. low": "90",
                    "4. close": "100",
                    "5. adjusted close": "50",
                    "6. volume": "1234",
                    "7. dividend amount": "0",
                    "8. split coefficient": "1",
                }
            }
        }
        rows = _adjusted_daily_rows(payload)
        self.assertEqual(rows[0]["open"], 50.0)
        self.assertEqual(rows[0]["close"], 50.0)
        self.assertEqual(rows[0]["volume"], 1234.0)

    def test_symbol_contract_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "symbols.txt"
            path.write_text(
                "\n".join(f"T{index:03d}" for index in range(101)) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(len(read_symbols(path)), 101)
            path.write_text("QQQ\n" + path.read_text(encoding="utf-8"))
            with self.assertRaises(ValueError):
                read_symbols(path)

    def test_horizon_split_has_exact_pretest_embargo(self) -> None:
        dates = [
            value.strftime("%Y-%m-%d")
            for value in pd.bdate_range("2025-01-01", periods=200)
        ]
        for horizon in (5, 20):
            split = split_dates(dates, horizon)
            self.assertEqual(len(split["pre_test_embargo"]), horizon)
            self.assertFalse(
                set(split["development"]) & set(split["sealed_test"])
            )
            self.assertEqual(len(split["sealed_test"]), 30)

    def test_panel_rows_apply_coverage_and_create_both_labels(self) -> None:
        symbols = [f"T{index:03d}" for index in range(101)]
        dates = [
            value.strftime("%Y-%m-%d")
            for value in pd.bdate_range("2025-01-02", periods=180)
        ]

        def candles(offset: float) -> list[dict[str, float | str]]:
            output = []
            for index, market_date in enumerate(dates):
                close = 100.0 + offset + index * 0.05 + (index % 7) * 0.01
                output.append(
                    {
                        "market_date": market_date,
                        "open": close * 0.999,
                        "high": close * 1.01,
                        "low": close * 0.99,
                        "close": close,
                        "volume": 3_000_000.0 + index,
                    }
                )
            return output

        daily = {
            symbol: candles(index * 0.02)
            for index, symbol in enumerate(symbols)
        }
        daily["QQQ"] = candles(10.0)
        daily["SPY"] = candles(5.0)
        five = {name: 0.1 for name in FIVE_MINUTE_FEATURES}
        five["five_minute_regular_observed_bar_fraction"] = 1.0
        five["afterhours_observed_bar_fraction"] = 0.5
        intraday = {
            (symbol, market_date): dict(five)
            for symbol in symbols
            for market_date in dates[60:150]
        }
        frame, _ = build_rows(daily, symbols, intraday)
        self.assertGreaterEqual(frame["market_date"].nunique(), 60)
        self.assertEqual(frame["symbol"].nunique(), 101)
        self.assertFalse(frame.isna().any().any())
        for horizon in (5, 20):
            self.assertIn(
                f"label_{horizon}d_cross_sectional_rank",
                frame.columns,
            )
            self.assertTrue(
                (
                    frame[f"label_{horizon}d_entry_date"]
                    > frame["market_date"]
                ).all()
            )


if __name__ == "__main__":
    unittest.main()
