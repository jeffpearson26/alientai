import unittest

from alientai_v2.portfolio_manager import approve_candidate_buy


class PortfolioManagerShareCapTests(unittest.TestCase):
    def test_optional_paper_share_cap_limits_approval(self):
        account = {"cash": 20000.0, "open_positions": {}, "closed_trades": [], "trade_log": []}
        settings = {
            "starting_cash": 20000.0,
            "max_open_positions": 5,
            "max_invested_dollars": 9000.0,
            "target_invested_dollars": 9000.0,
            "target_cash_reserve_dollars": 1000.0,
            "max_single_share_price": 2500.0,
            "small_position_dollars": 500.0,
            "max_shares_per_paper_trade": 1,
        }
        result = approve_candidate_buy(
            account=account,
            settings=settings,
            candidate={"symbol": "AAA", "price": 50.0, "score": 80.0, "decision": "BUY_CANDIDATE"},
        )
        self.assertTrue(result["approved"])
        self.assertEqual(1, result["shares"])


if __name__ == "__main__":
    unittest.main()
