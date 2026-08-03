import unittest

from evaluate_ai_semiconductor_narrative_outcomes import build_outcomes


class NarrativeOutcomeTests(unittest.TestCase):
    def test_one_day_enters_next_open_and_exits_same_close(self):
        observations = [{
            "model_id": "model",
            "model_sha256": "hash",
            "symbol": "AMD",
            "market_date": "2026-01-02",
            "target_horizon_sessions": 1,
        }]
        daily = {"AMD": ([
            ("2026-01-02", 100.0, 100.0),
            ("2026-01-05", 101.0, 103.0),
        ], "source")}
        complete, pending = build_outcomes(observations, daily, "2026-01-05")
        self.assertFalse(pending)
        self.assertEqual(complete[0]["entry_open"], 101.0)
        self.assertEqual(complete[0]["exit_close"], 103.0)
        self.assertAlmostEqual(
            complete[0]["net_return_pct"], (103 / 101 - 1) * 100 - 0.25
        )

    def test_future_exit_remains_pending(self):
        observations = [{
            "model_id": "model", "symbol": "AMD", "market_date": "2026-01-02",
            "target_horizon_sessions": 1,
        }]
        daily = {"AMD": ([
            ("2026-01-02", 100.0, 100.0),
            ("2026-01-05", 101.0, 103.0),
        ], "source")}
        complete, pending = build_outcomes(observations, daily, "2026-01-02")
        self.assertFalse(complete)
        self.assertEqual(pending[0]["status"], "pending_horizon")


if __name__ == "__main__":
    unittest.main()
