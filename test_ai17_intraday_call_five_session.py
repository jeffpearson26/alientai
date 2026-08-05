from __future__ import annotations

import unittest

import numpy as np

from train_ai17_intraday_call_five_session import choose


class Ai17IntradayCallFiveSessionTests(unittest.TestCase):
    def test_choose_allows_full_abstention(self) -> None:
        rows = [
            {
                "symbol": "AMD",
                "call_features_available": True,
                "call_activity_history_count": 20,
                "call_volume_unusual": True,
            }
        ]
        self.assertEqual(choose(rows, np.asarray([0.50])), [])

    def test_choose_requires_previous_call_history(self) -> None:
        rows = [
            {
                "symbol": "AMD",
                "call_features_available": True,
                "call_activity_history_count": 9,
                "call_volume_unusual": True,
            }
        ]
        self.assertEqual(choose(rows, np.asarray([0.90])), [])

    def test_choose_caps_at_five(self) -> None:
        rows = [
            {
                "symbol": f"S{index}",
                "call_features_available": True,
                "call_activity_history_count": 20,
                "call_volume_unusual": True,
            }
            for index in range(7)
        ]
        selected = choose(rows, np.linspace(0.6, 0.9, 7))
        self.assertEqual(len(selected), 5)
        self.assertEqual(selected[0]["symbol"], "S6")


if __name__ == "__main__":
    unittest.main()
