import json
import unittest
from unittest.mock import patch

from alientai_v2 import v2_routes


class EngineAccountAttributionTests(unittest.TestCase):
    def summary(self):
        account = {
            "open_positions": {
                "AAA": {
                    "symbol": "AAA", "engine_id": "engine_a", "shares": 1,
                    "entry_price": 100, "last_price": 110, "cost": 100,
                },
                "BBB": {
                    "symbol": "BBB", "engine_id": "engine_b", "shares": 1,
                    "entry_price": 50, "last_price": 40, "cost": 50,
                },
            },
            "closed_trades": [
                {"symbol": "CCC", "engine_id": "engine_a", "pnl": 5},
                {"symbol": "DDD", "engine_id": "old_engine", "pnl": 999},
            ],
        }
        with (
            patch.object(v2_routes.Path, "exists", return_value=True),
            patch.object(v2_routes.Path, "read_text", return_value=json.dumps(account)),
            patch.object(v2_routes, "get_status", return_value={
                "enabled_engines": ["engine_a", "engine_b", "engine_empty"],
            }),
        ):
            return v2_routes._read_v2_engine_accounts_summary_file()

    def test_each_engine_receives_only_its_own_trades(self):
        rows = {row["engine_id"]: row for row in self.summary()["engines"]}
        self.assertEqual([row["symbol"] for row in rows["engine_a"]["open_positions"]], ["AAA"])
        self.assertEqual([row["symbol"] for row in rows["engine_a"]["closed_trades"]], ["CCC"])
        self.assertEqual([row["symbol"] for row in rows["engine_b"]["open_positions"]], ["BBB"])
        self.assertEqual(rows["engine_b"]["closed_trades"], [])

    def test_empty_enabled_engine_does_not_inherit_shared_account_results(self):
        row = {item["engine_id"]: item for item in self.summary()["engines"]}["engine_empty"]
        self.assertFalse(row["has_engine_trades"])
        self.assertEqual(row["open_positions_count"], 0)
        self.assertEqual(row["closed_trades_count"], 0)
        self.assertEqual(row["total_pnl"], 0.0)

    def test_disabled_engine_is_not_displayed(self):
        ids = {row["engine_id"] for row in self.summary()["engines"]}
        self.assertNotIn("old_engine", ids)


if __name__ == "__main__":
    unittest.main()
