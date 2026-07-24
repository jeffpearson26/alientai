import unittest

from compile_natural_options_daily_panel import prior_rows


class NaturalOptionsDailyPanelTests(unittest.TestCase):
    def test_prior_rows_exclude_target_and_future_data(self):
        rows = [
            {"symbol": "abc", "market_date": "2026-07-21", "option_call_volume": 10, "option_call_open_interest": 20},
            {"symbol": "ABC", "market_date": "2026-07-22", "option_call_volume": 99, "option_call_open_interest": 20},
            {"symbol": "ABC", "market_date": "2026-07-23", "option_call_volume": 99, "option_call_open_interest": 20},
        ]
        self.assertEqual(prior_rows(rows, "2026-07-22"), [{"symbol": "ABC", "market_date": "2026-07-21", "option_call_volume": 10, "option_call_open_interest": 20}])


if __name__ == "__main__":
    unittest.main()
