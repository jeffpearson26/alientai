from __future__ import annotations

import unittest

from evaluate_unusual_call_outcomes import join_option_outcomes


class UnusualCallOutcomeTests(unittest.TestCase):
    def test_joins_only_matching_symbol_date(self):
        base = [{"symbol": "AAA", "market_date": "2026-01-01", "label_forward_return_5d_pct": 1.0}]
        options = [{"symbol": "AAA", "market_date": f"2026-01-{day:02d}", "option_call_volume": 10 + day, "option_call_open_interest": 100} for day in range(1, 12)]
        joined = join_option_outcomes(base, options)
        self.assertEqual(1, len(joined))
        self.assertEqual("AAA", joined[0]["symbol"])


if __name__ == "__main__":
    unittest.main()
