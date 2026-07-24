import unittest

from contextual_options_stop_evaluator import stopped_return


class ContextualOptionsStopEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.row = {"market_date": "2026-01-02", "future_market_date": "2026-01-09", "close": 100.0}

    def test_gap_through_stop_uses_open_price(self):
        path = [
            {"date": "2026-01-03", "open": "92", "low": "90", "close": "91"},
            *[{"date": f"2026-01-0{day}", "open": "100", "low": "99", "close": "100"} for day in range(4, 8)],
        ]
        result = stopped_return(self.row, path, -5.0)
        self.assertEqual(result, {"return_pct": -8.0, "exit_date": "2026-01-03", "stopped": True})

    def test_intraday_stop_uses_stop_price(self):
        path = [
            {"date": "2026-01-03", "open": "99", "low": "94", "close": "96"},
            *[{"date": f"2026-01-0{day}", "open": "100", "low": "99", "close": "100"} for day in range(4, 8)],
        ]
        self.assertEqual(stopped_return(self.row, path, -5.0)["return_pct"], -5.0)

    def test_holds_to_five_session_close_without_stop(self):
        path = [
            {"date": f"2026-01-0{day}", "open": "100", "low": "96", "close": str(100 + day)} for day in range(3, 8)
        ]
        result = stopped_return(self.row, path, -5.0)
        self.assertFalse(result["stopped"])
        self.assertEqual(result["return_pct"], 7.0)


if __name__ == "__main__":
    unittest.main()
