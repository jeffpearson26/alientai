from __future__ import annotations

import unittest

from contextual_options_shadow_adapter import build_payload, validate_daily_panel


def rows(count: int = 400):
    return [
        {
            "symbol": f"S{index:03d}",
            "market_date": "2026-07-23",
            "technical_context_score": float(index),
            "call_volume_unusual": index >= count - 3,
            "call_activity_history_count": 10,
        }
        for index in range(count)
    ]


class ContextualOptionsShadowAdapterTests(unittest.TestCase):
    def test_builds_non_executing_payload_from_complete_panel(self):
        payload = build_payload(rows())
        self.assertEqual("research_payload_ready", payload["status"])
        self.assertFalse(payload["execution_enabled"])
        self.assertEqual(3, len(payload["candidates"]))

    def test_rejects_partial_universe(self):
        with self.assertRaises(ValueError):
            validate_daily_panel(rows(399))

    def test_rejects_inadequate_history(self):
        panel = rows()
        for row in panel[:100]:
            row["call_activity_history_count"] = 9
        with self.assertRaises(ValueError):
            validate_daily_panel(panel)


if __name__ == "__main__":
    unittest.main()
