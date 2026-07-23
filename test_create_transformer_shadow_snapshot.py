from __future__ import annotations

import unittest

from create_transformer_shadow_snapshot import record


class TransformerShadowSnapshotTests(unittest.TestCase):
    def test_record_is_non_executing_and_defers_outcome(self) -> None:
        item = record("ABC", "2026-07-21", 0.61, 20)
        self.assertEqual(item["decision"], "SHADOW_JOURNAL_ONLY")
        self.assertFalse(item["execution_enabled"])
        self.assertEqual(item["outcome_not_due_before"], "2026-08-18")


if __name__ == "__main__":
    unittest.main()
