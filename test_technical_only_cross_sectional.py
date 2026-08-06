from __future__ import annotations

import unittest

from audit_technical_only_cross_sectional_panel import EXCLUDED_TOKENS
from train_multiresolution_cross_sectional import feature_columns


class TechnicalOnlyCrossSectionalTests(unittest.TestCase):
    def test_daily_feature_set_contains_no_excluded_family(self) -> None:
        for column in feature_columns("daily_only"):
            self.assertFalse(
                any(token in column.lower() for token in EXCLUDED_TOKENS),
                msg=f"excluded feature entered technical model: {column}",
            )

    def test_qqq_spy_context_is_retained(self) -> None:
        columns = feature_columns("daily_only")
        self.assertIn("context_qqq_return_5d_pct", columns)
        self.assertIn("context_spy_return_20d_pct", columns)
        self.assertIn("rank_daily_relative_strength_qqq_5d_pct", columns)
        self.assertIn("rank_daily_relative_strength_spy_5d_pct", columns)


if __name__ == "__main__":
    unittest.main()
