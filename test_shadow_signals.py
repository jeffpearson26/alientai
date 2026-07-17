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


if __name__ == "__main__":
    unittest.main()
