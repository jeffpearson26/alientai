from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from run_full_nasdaq_5min_after_daily import active_alpha_collectors


class FakeProcess:
    def __init__(self, pid: int, name: str, command: list[str]) -> None:
        self.info = {
            "pid": pid,
            "name": name,
            "cmdline": command,
        }


class FullNasdaqQueueTests(unittest.TestCase):
    def test_duplicate_detection_ignores_non_python_command_text(self) -> None:
        processes = [
            FakeProcess(
                1001,
                "powershell.exe",
                [
                    "powershell.exe",
                    "-Command",
                    "inspect download_alpha_vantage_full_nasdaq_5min.py",
                ],
            ),
            FakeProcess(
                1002,
                "python.exe",
                [
                    "python.exe",
                    "download_alpha_vantage_full_nasdaq_daily.py",
                ],
            ),
            FakeProcess(
                os.getpid(),
                "python.exe",
                [
                    "python.exe",
                    "download_alpha_vantage_full_nasdaq_5min.py",
                ],
            ),
        ]
        with patch(
            "run_full_nasdaq_5min_after_daily.psutil.process_iter",
            return_value=processes,
        ):
            actual = active_alpha_collectors()

        self.assertEqual(1, len(actual))
        self.assertEqual(1002, actual[0]["pid"])

    def test_duplicate_detection_ignores_the_queue_runner(self) -> None:
        processes = [
            FakeProcess(
                2001,
                "python.exe",
                [
                    "python.exe",
                    "run_full_nasdaq_5min_after_daily.py",
                    "--daily-archive",
                    "download_alpha_vantage_reference",
                ],
            )
        ]
        with patch(
            "run_full_nasdaq_5min_after_daily.psutil.process_iter",
            return_value=processes,
        ):
            self.assertEqual([], active_alpha_collectors())


if __name__ == "__main__":
    unittest.main()
