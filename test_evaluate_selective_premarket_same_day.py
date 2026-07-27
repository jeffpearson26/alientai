import unittest

from evaluate_selective_premarket_same_day import same_day_net_return


class PremarketSameDayTests(unittest.TestCase):
    def test_uses_first_regular_close_and_final_close_minus_cost(self):
        rows = [
            {"timestamp": "2026-01-02 09:25:00", "close": "90"},
            {"timestamp": "2026-01-02 09:30:00", "close": "100"},
            {"timestamp": "2026-01-02 16:00:00", "close": "110"},
        ]
        self.assertAlmostEqual(same_day_net_return(rows, "2026-01-02"), 9.75)

    def test_nonstandard_session_fails_closed(self):
        rows = [
            {"timestamp": "2026-01-02 09:35:00", "close": "100"},
            {"timestamp": "2026-01-02 15:55:00", "close": "110"},
        ]
        self.assertIsNone(same_day_net_return(rows, "2026-01-02"))


if __name__ == "__main__":
    unittest.main()
