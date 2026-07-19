from __future__ import annotations

import unittest

from alientai_v2.research.historical_call_evaluator import evaluate_trade, select_call


def option(contract, strike, expiration, bid, ask, delta, oi=100, volume=10):
    return {"contractID": contract, "type": "call", "strike": str(strike), "expiration": expiration, "bid": str(bid), "ask": str(ask), "delta": str(delta), "open_interest": str(oi), "volume": str(volume), "implied_volatility": "0.30"}


class HistoricalCallEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.row = {"symbol": "IBM", "study_role": "winner", "market_date": "2024-01-02", "future_market_date": "2024-01-09", "close": 100, "label_forward_return_5d_pct": 10}
        self.entry = [
            option("ATM", 100, "2024-02-02", 4.8, 5.0, 0.52),
            option("D60", 95, "2024-02-02", 7.8, 8.0, 0.60),
        ]
        self.exit = [
            option("ATM", 100, "2024-02-02", 9.8, 10.0, 0.70),
            option("D60", 95, "2024-02-02", 12.8, 13.0, 0.78),
        ]

    def test_strategy_selection_uses_entry_data(self):
        from datetime import date
        self.assertEqual(select_call(self.entry, 100, date(2024, 1, 2), date(2024, 1, 9), "atm_30d")["contractID"], "ATM")
        self.assertEqual(select_call(self.entry, 100, date(2024, 1, 2), date(2024, 1, 9), "delta60_30d")["contractID"], "D60")

    def test_uses_entry_ask_and_exit_bid_with_commissions(self):
        trade = evaluate_trade(self.row, self.entry, self.exit, "atm_30d", commission_per_contract=0.65)
        expected = ((9.8 * 100 - 0.65) / (5.0 * 100 + 0.65) - 1) * 100
        self.assertAlmostEqual(trade["net_call_return_pct"], expected)

    def test_rejects_missing_exit_contract(self):
        self.assertIsNone(evaluate_trade(self.row, self.entry, [], "atm_30d"))


if __name__ == "__main__":
    unittest.main()
