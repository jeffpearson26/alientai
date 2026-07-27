import unittest
from datetime import date, timedelta

from train_multi_horizon_pullback import build_examples, net_return


def rows(count=140):
    output = []
    for index in range(count):
        close = 100.0 * (1.002 ** index)
        output.append({
            "symbol": "AAA",
            "date": f"2026-01-{index + 1:02d}" if index < 28 else f"2026-02-{index - 27:02d}",
            "open": close,
            "close": close,
        })
    return output


class TrainPullbackTests(unittest.TestCase):
    def test_invalid_price_window_is_excluded_not_fatal(self):
        start = date(2025, 1, 1)
        candles = [
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "open": 100.0 + index,
                "close": 100.0 + index,
            }
            for index in range(140)
        ]
        candles[100]["close"] = "0"
        result = build_examples(
            "AAA", candles, step_days=1, round_trip_cost_pct=0.25
        )
        self.assertEqual(result, [])

    def test_net_return_uses_next_open_and_horizon_close_minus_cost(self):
        candles = [
            {"date": "2026-01-02", "open": 99, "close": 100},
            {"date": "2026-01-05", "open": 100, "close": 101},
            {"date": "2026-01-06", "open": 101, "close": 110},
        ]
        self.assertAlmostEqual(net_return(candles, 0, 2, 0.25), 9.75)

    def test_long_calendar_gap_is_excluded(self):
        candles = [
            {"date": "2026-01-02", "open": 99, "close": 100},
            {"date": "2026-01-20", "open": 100, "close": 101},
            {"date": "2026-01-21", "open": 101, "close": 102},
        ]
        self.assertIsNone(net_return(candles, 0, 2, 0.25))


if __name__ == "__main__":
    unittest.main()
