from __future__ import annotations

import unittest

from export_contextual_options_selected_events import select_events


class ExportContextualEventsTests(unittest.TestCase):
    def test_selection_uses_calibration_cutoff_and_requires_unusual_calls(self):
        calibration = [
            {"technical_context_score": 0.1},
            {"technical_context_score": 0.2},
            {"technical_context_score": 0.3},
            {"technical_context_score": 0.4},
        ]
        test = [
            {
                "symbol": "AAA", "market_date": "2026-01-10",
                "future_market_date": "2026-01-15",
                "technical_context_score": 0.5, "call_volume_unusual": True,
            },
            {
                "symbol": "BBB", "market_date": "2026-01-10",
                "future_market_date": "2026-01-15",
                "technical_context_score": 0.6, "call_volume_unusual": False,
            },
        ]
        cutoff, selected = select_events(calibration, test, 0.25, 5)
        self.assertAlmostEqual(0.325, cutoff)
        self.assertEqual(["AAA"], [row["symbol"] for row in selected])


if __name__ == "__main__":
    unittest.main()
