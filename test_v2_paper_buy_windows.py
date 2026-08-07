from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from alientai_v2.engine import market_buy_window_status


class V2PaperBuyWindowTests(unittest.TestCase):
    def at(self, hour: int, minute: int, **settings):
        now = datetime(2026, 8, 7, hour, minute, tzinfo=ZoneInfo("America/Los_Angeles"))
        return market_buy_window_status(settings, now_local_dt=now)

    def test_afterhours_enabled_from_after_regular_close_through_five(self):
        settings = {"allow_afterhours_buys": True, "afterhours_buy_end_minutes": 1020}
        self.assertEqual(self.at(13, 1, **settings)["session"], "afterhours")
        self.assertTrue(self.at(16, 59, **settings)["new_buys_allowed"])
        self.assertTrue(self.at(17, 0, **settings)["new_buys_allowed"])

    def test_afterhours_disabled_setting_fails_closed(self):
        result = self.at(14, 0, allow_afterhours_buys=False)
        self.assertFalse(result["new_buys_allowed"])
        self.assertEqual(result["session"], "closed")

    def test_after_five_pm_fails_closed(self):
        result = self.at(
            17, 1, allow_afterhours_buys=True, afterhours_buy_end_minutes=1020
        )
        self.assertFalse(result["new_buys_allowed"])
        self.assertEqual(result["session"], "closed")

    def test_regular_session_remains_enabled(self):
        result = self.at(12, 0, allow_afterhours_buys=True)
        self.assertTrue(result["new_buys_allowed"])
        self.assertEqual(result["session"], "regular")


if __name__ == "__main__":
    unittest.main()
