from __future__ import annotations

import unittest

from score_alpha_vantage_nasdaq_snapshot import safe_name


class AlphaVantageNasdaqSnapshotTests(unittest.TestCase):
    def test_safe_name_matches_daily_collector_convention(self) -> None:
        self.assertEqual(safe_name("BRK.B"), "BRK-B")
        self.assertEqual(safe_name("ABC/DEF"), "ABC-DEF")


if __name__ == "__main__":
    unittest.main()
