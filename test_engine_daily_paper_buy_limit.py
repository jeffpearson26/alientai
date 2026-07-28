from __future__ import annotations

import unittest

from alientai_v2.engine import paper_buys_on_market_day


class EngineDailyPaperBuyLimitTests(unittest.TestCase):
    def test_counts_only_buy_actions_on_requested_day(self) -> None:
        account = {"trade_log": [
            {"time": "2026-07-28T08:00:00", "action": "BUY"},
            {"time": "2026-07-28T09:00:00", "action": "SELL"},
            {"time": "2026-07-27T08:00:00", "action": "BUY"},
            {"time": "2026-07-28T10:00:00", "action": "buy"},
        ]}
        self.assertEqual(
            paper_buys_on_market_day(account, {}, "2026-07-28"), 2
        )

    def test_invalid_trade_log_fails_closed_to_zero(self) -> None:
        self.assertEqual(paper_buys_on_market_day({"trade_log": {}}, {}, "2026-07-28"), 0)


if __name__ == "__main__":
    unittest.main()
