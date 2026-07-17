from __future__ import annotations

import unittest
from unittest.mock import patch

from alientai_v2 import engine


def make_account(*, exit_rule: str | None = None) -> dict:
    position = {
        "symbol": "TEST",
        "shares": 5,
        "entry_price": 100.0,
        "highest_price": 100.0,
        "entry_time": "2026-07-17T06:00:00-07:00",
        "minimum_hold_minutes": 28_800.0,
        "allow_stop_before_min_hold": False,
        "allow_trailing_before_min_hold": False,
        "allow_take_profit_before_min_hold": False,
    }
    if exit_rule:
        position["exit_rule"] = exit_rule
        position["scheduled_exit_time"] = "2099-01-01T12:00:00-08:00"
    return {"open_positions": {"TEST": position}}


def make_settings(**overrides) -> dict:
    settings = {
        "take_profit_pct": 3.0,
        "stop_loss_pct": -1.5,
        "trailing_stop_pct": 1.0,
        "trailing_stop_activation_pct": 1.0,
        "prediction_horizon_days": 20.0,
        "minimum_hold_minutes": 28_800.0,
        "max_hold_minutes": 28_800.0,
        "emergency_stop_enabled": True,
        "emergency_stop_loss_pct": -5.0,
    }
    settings.update(overrides)
    return settings


class EmergencyStopTests(unittest.TestCase):
    def run_manager(self, price: float, *, account=None, settings=None):
        account = account or make_account()
        settings = settings or make_settings()

        def fake_sell(_account, symbol, exit_price, reason):
            return {
                "symbol": symbol,
                "exit_price": exit_price,
                "reason": reason,
            }

        quotes = [{"symbol": "TEST", "price": price, "source": "test"}]
        with (
            patch.object(engine, "get_real_v2_quotes", return_value=quotes),
            patch.object(engine, "minutes_since_iso", return_value=60.0),
            patch.object(engine, "sell_position", side_effect=fake_sell),
        ):
            return engine.manage_open_positions(account, settings), account

    def test_emergency_stop_bypasses_twenty_day_minimum_hold(self):
        actions, account = self.run_manager(94.0)
        self.assertEqual(len(actions), 1)
        self.assertIn("V2 emergency stop", actions[0]["reason"])
        self.assertFalse(account["open_positions"]["TEST"]["min_hold_complete"])

    def test_emergency_stop_bypasses_future_friday_exit(self):
        account = make_account(exit_rule="friday_noon_pacific")
        actions, _ = self.run_manager(94.0, account=account)
        self.assertEqual(len(actions), 1)
        self.assertIn("V2 emergency stop", actions[0]["reason"])

    def test_loss_above_emergency_limit_remains_held(self):
        actions, account = self.run_manager(96.0)
        self.assertEqual(actions, [])
        self.assertEqual(
            account["open_positions"]["TEST"]["last_sell_blocked_reason"],
            "stop loss blocked before minimum hold",
        )

    def test_emergency_stop_can_be_explicitly_disabled(self):
        actions, account = self.run_manager(
            90.0,
            settings=make_settings(emergency_stop_enabled=False),
        )
        self.assertEqual(actions, [])
        self.assertEqual(
            account["open_positions"]["TEST"]["last_sell_blocked_reason"],
            "stop loss blocked before minimum hold",
        )

    def test_recent_stop_blocks_reentry(self):
        account = {
            "closed_trades": [{
                "time": "2026-07-17T06:32:54-07:00",
                "symbol": "TEST",
                "reason": "V2 emergency stop at -6.0% (limit -5.0%)",
            }]
        }
        with patch.object(engine, "minutes_since_iso", return_value=4.0):
            reason = engine.symbol_stop_cooldown_reason(
                account,
                "test",
                make_settings(
                    stop_reentry_cooldown_enabled=True,
                    stop_reentry_cooldown_hours=168.0,
                ),
            )
        self.assertIn("cooldown active", reason)

    def test_expired_stop_allows_reentry(self):
        account = {
            "closed_trades": [{
                "time": "2026-07-01T06:32:54-07:00",
                "symbol": "TEST",
                "reason": "V2 stop loss after minimum hold",
            }]
        }
        with patch.object(engine, "minutes_since_iso", return_value=10_081.0):
            reason = engine.symbol_stop_cooldown_reason(
                account,
                "TEST",
                make_settings(stop_reentry_cooldown_hours=168.0),
            )
        self.assertEqual("", reason)

    def test_non_stop_sale_does_not_trigger_cooldown(self):
        account = {
            "closed_trades": [{
                "time": "2026-07-17T06:32:54-07:00",
                "symbol": "TEST",
                "reason": "V2 take profit",
            }]
        }
        with patch.object(engine, "minutes_since_iso", return_value=4.0):
            reason = engine.symbol_stop_cooldown_reason(
                account,
                "TEST",
                make_settings(),
            )
        self.assertEqual("", reason)


if __name__ == "__main__":
    unittest.main()
