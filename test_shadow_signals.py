from __future__ import annotations

import unittest

from alientai_v2.shadow_signals import build_new_records


class ShadowSignalTests(unittest.TestCase):
    def test_records_buy_candidate(self):
        rows = [{"symbol": "aapl", "engine_id": "test", "decision": "BUY_CANDIDATE", "score": 77, "price": 100}]
        records = build_new_records(rows, {}, "2026-07-17T08:00:00", set())
        self.assertEqual(1, len(records))
        self.assertEqual("AAPL", records[0]["symbol"])
        self.assertEqual(100.0, records[0]["observed_price"])

    def test_deduplicates_same_engine_symbol_decision_and_day(self):
        row = {"symbol": "AAPL", "engine_id": "test", "decision": "BUY_CANDIDATE"}
        seen = set()
        self.assertEqual(1, len(build_new_records([row], {}, "2026-07-17T08:00:00", seen)))
        self.assertEqual(0, len(build_new_records([row], {}, "2026-07-17T09:00:00", seen)))

    def test_allows_signal_on_later_day(self):
        row = {"symbol": "AAPL", "engine_id": "test", "decision": "BUY_CANDIDATE"}
        seen = set()
        build_new_records([row], {}, "2026-07-17T08:00:00", seen)
        self.assertEqual(1, len(build_new_records([row], {}, "2026-07-18T08:00:00", seen)))

    def test_ignores_watch_by_default(self):
        row = {"symbol": "AAPL", "engine_id": "test", "decision": "WATCH"}
        self.assertEqual([], build_new_records([row], {}, "2026-07-17T08:00:00", set()))

    def test_watch_can_be_configured(self):
        row = {"symbol": "AAPL", "engine_id": "test", "decision": "WATCH"}
        settings = {"shadow_signal_decisions": ["WATCH"]}
        self.assertEqual(1, len(build_new_records([row], settings, "2026-07-17T08:00:00", set())))

    def test_shadow_research_override_does_not_change_execution_decision(self):
        row = {
            "symbol": "NVDA",
            "engine_id": "transformer_20day",
            "decision": "AVOID",
            "shadow_research_decision": "BUY_CANDIDATE",
            "price": 200.0,
            "prediction_horizon_minutes": 28800,
        }
        record = build_new_records([row], {}, "2026-07-17T08:00:00", set())[0]
        self.assertEqual("BUY_CANDIDATE", record["decision"])
        self.assertEqual("AVOID", record["execution_decision"])
        self.assertTrue(record["shadow_research_only"])

    def test_preserves_scheduled_exit_and_execution_eligibility(self):
        row = {
            "symbol": "CACI",
            "engine_id": "prediction_friday",
            "decision": "BUY_CANDIDATE",
            "scheduled_exit_time": "2026-07-17T12:00:00-07:00",
            "exit_rule": "friday_noon_pacific",
            "spread_percent": 0.47,
        }
        settings = {
            "paper_trading_enabled": False,
            "main_account_enabled_buy_engines": [],
        }
        record = build_new_records([row], settings, "2026-07-17T08:00:00", set())[0]
        self.assertEqual("2026-07-17T12:00:00-07:00", record["scheduled_exit_time"])
        self.assertEqual("friday_noon_pacific", record["exit_rule"])
        self.assertEqual(0.47, record["spread_percent"])
        self.assertFalse(record["main_account_allowlisted"])
        self.assertFalse(record["paper_trading_enabled_at_signal"])


if __name__ == "__main__":
    unittest.main()
