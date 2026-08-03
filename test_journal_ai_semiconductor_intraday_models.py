import tempfile
import unittest
from pathlib import Path

from journal_ai_semiconductor_intraday_models import append_unique, merge_inputs
from build_prospective_call_features import target_features
from evaluate_intraday_prospective_outcomes import completed_outcomes


class IntradayJournalTests(unittest.TestCase):
    def test_merge_enforces_prior_and_current_timing(self):
        tech = [{"symbol": "NVDA", "market_date": "2026-07-30", "technical_rsi_2": 10}]
        pm = [{
            "symbol": "NVDA",
            "market_date": "2026-07-31",
            "premarket_available": True,
            "premarket_cutoff_et": "09:25",
            "premarket_last_timestamp_et": "2026-07-31 09:25:00",
            "premarket_bar_count": 66,
            "premarket_gap_pct": 1,
        }]
        calls = [{"symbol": "NVDA", "market_date": "2026-07-30", "call_volume_unusual": False}]
        result = merge_inputs(tech, pm, calls, "2026-07-31", ["NVDA"])
        self.assertEqual(result[0]["technical_rsi_2"], 10)
        self.assertEqual(result[0]["model_premarket_gap_pct"], 1)
        self.assertEqual(result[0]["model_call_volume_unusual"], False)

    def test_merge_rejects_same_day_close_features(self):
        row = {"symbol": "NVDA", "market_date": "2026-07-31"}
        pm = [{
            **row,
            "premarket_available": True,
            "premarket_cutoff_et": "09:25",
            "premarket_last_timestamp_et": "2026-07-31 09:25:00",
            "premarket_bar_count": 66,
        }]
        with self.assertRaisesRegex(ValueError, "prior market date"):
            merge_inputs([row], pm, [row], "2026-07-31")

    def test_merge_rejects_partial_or_delayed_premarket_panel(self):
        tech = [{"symbol": "NVDA", "market_date": "2026-07-30"}]
        calls = [{"symbol": "NVDA", "market_date": "2026-07-30"}]
        delayed = [{
            "symbol": "NVDA",
            "market_date": "2026-07-31",
            "premarket_available": True,
            "premarket_cutoff_et": "09:25",
            "premarket_last_timestamp_et": "2026-07-31 09:20:00",
            "premarket_bar_count": 65,
        }]
        with self.assertRaisesRegex(ValueError, "fresh 09:25"):
            merge_inputs(tech, delayed, calls, "2026-07-31", ["NVDA"])
        complete = [{**delayed[0], "premarket_last_timestamp_et": "2026-07-31 09:25:00"}]
        with self.assertRaisesRegex(ValueError, "frozen symbols"):
            merge_inputs(tech, complete, calls, "2026-07-31", ["NVDA", "AMD"])

    def test_append_is_model_specific_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.jsonl"
            rows = [
                {"model_id": "a", "market_date": "2026-07-31", "symbol": "NVDA"},
                {"model_id": "b", "market_date": "2026-07-31", "symbol": "NVDA"},
            ]
            self.assertEqual(append_unique(path, rows), 2)
            self.assertEqual(append_unique(path, rows), 0)

    def test_call_features_use_only_history_before_target(self):
        historical = [
            {"symbol": "NVDA", "market_date": "2026-07-01", "option_call_volume": 10, "option_call_open_interest": 100},
            {"symbol": "NVDA", "market_date": "2026-08-01", "option_call_volume": 9999, "option_call_open_interest": 100},
        ]
        current = [
            {"symbol": "NVDA", "market_date": "2026-07-30", "option_call_volume": 20, "option_call_open_interest": 100},
        ]
        result = target_features(historical, current, "2026-07-30")
        self.assertEqual(result[0]["call_activity_history_count"], 1)

    def test_outcome_requires_complete_horizon(self):
        observation = {
            "model_id": "m", "model_sha256": "h", "market_date": "2026-07-31",
            "symbol": "NVDA", "rank": 1, "model_score": 0.5, "horizon_minutes": 60,
        }
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(completed_outcomes([observation], Path(directory)), [])


if __name__ == "__main__":
    unittest.main()
