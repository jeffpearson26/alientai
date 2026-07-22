from __future__ import annotations

import unittest

from alientai_v2.research.unusual_call_activity import unusual_call_features


class UnusualCallActivityTests(unittest.TestCase):
    def test_uses_only_prior_symbol_history(self):
        rows = [{"symbol": "AAA", "market_date": f"2026-01-{day:02d}", "option_call_volume": 10, "option_call_open_interest": 100} for day in range(1, 11)]
        rows.append({"symbol": "AAA", "market_date": "2026-01-11", "option_call_volume": 100, "option_call_open_interest": 100})
        result = unusual_call_features(rows, lookback=10, minimum_history=10)
        self.assertEqual(10, result[-1]["call_activity_history_count"])
        self.assertIsNone(result[-1]["call_volume_zscore"])

    def test_flags_large_volume_against_variable_prior_history(self):
        rows = [{"symbol": "AAA", "market_date": f"2026-02-{day:02d}", "option_call_volume": 10 + (day % 2), "option_call_open_interest": 100} for day in range(1, 11)]
        rows.append({"symbol": "AAA", "market_date": "2026-02-11", "option_call_volume": 100, "option_call_open_interest": 100})
        result = unusual_call_features(rows, lookback=10, minimum_history=10)
        self.assertTrue(result[-1]["call_volume_unusual"])


if __name__ == "__main__":
    unittest.main()
