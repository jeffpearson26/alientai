from datetime import datetime, timedelta
import unittest
from unittest.mock import patch

from alientai_v2.engine import manage_open_positions
from alientai_v2.paper_account import buy_position
from alientai_v2.portfolio_manager import approve_candidate_buy


MODEL_ID = "nasdaq100_complete_101_baseline_v1"


def candidate(price: float = 100.0, pyramid: bool = False) -> dict:
    return {
        "symbol": "AAPL",
        "engine_id": MODEL_ID,
        "decision": "BUY_CANDIDATE",
        "price": price,
        "score": 100.0,
        "requested_position_dollars": price,
        "paper_pyramid_allowed": pyramid,
        "paper_pyramid_interval_seconds": 300,
        "prediction_horizon_days": 5,
        "minimum_hold_minutes": 7200,
        "emergency_stop_enabled": True,
        "emergency_stop_loss_pct": -1.0,
        "stop_loss_pct": -1.0,
        "trailing_stop_pct": 5.0,
        "trailing_stop_activation_pct": 0.0,
        "allow_stop_before_min_hold": True,
        "allow_trailing_before_min_hold": True,
    }


def settings() -> dict:
    return {
        "starting_cash": 20_000.0,
        "max_open_positions": 5,
        "max_single_share_price": 2_500.0,
        "target_invested_dollars": 9_000.0,
        "max_invested_dollars": 9_000.0,
        "target_cash_reserve_dollars": 1_000.0,
    }


class Nasdaq101PaperExecutionControlTests(unittest.TestCase):
    def risk_position(self) -> dict:
        return {
            "symbol": "AAPL",
            "engine_id": MODEL_ID,
            "shares": 1,
            "entry_price": 100.0,
            "risk_entry_price": 100.0,
            "last_price": 100.0,
            "highest_price": 100.0,
            "entry_time": datetime.now().isoformat(timespec="seconds"),
            "minimum_hold_minutes": 7200,
            "cost": 100.0,
            "emergency_stop_enabled": True,
            "emergency_stop_loss_pct": -1.0,
            "stop_loss_pct": -1.0,
            "trailing_stop_pct": 5.0,
            "trailing_stop_activation_pct": 0.0,
            "allow_stop_before_min_hold": True,
            "allow_trailing_before_min_hold": True,
        }

    def test_initial_buy_copies_model_specific_risk_controls(self):
        account = {"cash": 20_000.0, "open_positions": {}, "trade_log": []}
        row = candidate()
        approval = approve_candidate_buy(account=account, settings=settings(), candidate=row)
        trade = buy_position(account, row, settings(), approval=approval)
        self.assertEqual(trade["action"], "BUY")
        position = account["open_positions"]["AAPL"]
        self.assertEqual(position["emergency_stop_loss_pct"], -1.0)
        self.assertEqual(position["trailing_stop_pct"], 5.0)
        self.assertTrue(position["allow_trailing_before_min_hold"])

    def test_uptrend_add_is_exactly_one_share_after_five_minutes(self):
        old_time = (datetime.now() - timedelta(minutes=6)).isoformat(timespec="seconds")
        account = {
            "cash": 19_900.0,
            "open_positions": {
                "AAPL": {
                    "symbol": "AAPL",
                    "engine_id": MODEL_ID,
                    "shares": 1,
                    "entry_price": 100.0,
                    "risk_entry_price": 100.0,
                    "last_price": 100.0,
                    "highest_price": 100.0,
                    "entry_time": old_time,
                    "last_add_time": old_time,
                    "cost": 100.0,
                },
            },
            "trade_log": [],
        }
        row = candidate(price=101.0, pyramid=True)
        approval = approve_candidate_buy(account=account, settings=settings(), candidate=row)
        self.assertTrue(approval["approved"])
        self.assertTrue(approval["pyramid"])
        self.assertEqual(approval["shares"], 1)
        trade = buy_position(account, row, settings(), approval=approval)
        self.assertEqual(trade["action"], "ADD")
        self.assertEqual(account["open_positions"]["AAPL"]["shares"], 2)
        self.assertEqual(account["open_positions"]["AAPL"]["risk_entry_price"], 100.0)

    def test_add_before_five_minutes_is_rejected(self):
        recent = datetime.now().isoformat(timespec="seconds")
        account = {
            "cash": 19_900.0,
            "open_positions": {
                "AAPL": {
                    "engine_id": MODEL_ID,
                    "shares": 1,
                    "entry_price": 100.0,
                    "entry_time": recent,
                    "last_add_time": recent,
                    "cost": 100.0,
                },
            },
        }
        approval = approve_candidate_buy(
            account=account, settings=settings(), candidate=candidate(101.0, True)
        )
        self.assertFalse(approval["approved"])

    @patch("alientai_v2.engine.get_real_v2_quotes")
    def test_one_percent_entry_stop_works_before_minimum_hold(self, quotes):
        quotes.return_value = [{"symbol": "AAPL", "price": 99.0}]
        account = {
            "cash": 19_900.0,
            "open_positions": {"AAPL": self.risk_position()},
            "closed_trades": [],
            "trade_log": [],
            "realized_pnl": 0.0,
        }
        actions = manage_open_positions(account, settings())
        self.assertEqual(actions[0]["action"], "SELL")
        self.assertIn("hard entry stop", actions[0]["reason"])

    @patch("alientai_v2.engine.get_real_v2_quotes")
    def test_five_percent_trailing_stop_works_before_minimum_hold(self, quotes):
        quotes.return_value = [{"symbol": "AAPL", "price": 104.5}]
        position = self.risk_position()
        position["highest_price"] = 110.0
        account = {
            "cash": 19_900.0,
            "open_positions": {"AAPL": position},
            "closed_trades": [],
            "trade_log": [],
            "realized_pnl": 0.0,
        }
        actions = manage_open_positions(account, settings())
        self.assertEqual(actions[0]["action"], "SELL")
        self.assertIn("5% trailing stop", actions[0]["reason"])


if __name__ == "__main__":
    unittest.main()
