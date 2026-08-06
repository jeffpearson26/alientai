from __future__ import annotations

import unittest

from audit_daily_options_cross_sectional_panel import EXCLUDED_TOKENS
from train_daily_options_cross_sectional import FEATURE_SETS, feature_columns


class DailyOptionsCrossSectionalTests(unittest.TestCase):
    def test_feature_sets_exclude_intraday_afterhours_and_news(self) -> None:
        for feature_set, features in FEATURE_SETS.items():
            for name in features:
                self.assertFalse(
                    any(token in name.lower() for token in EXCLUDED_TOKENS),
                    msg=f"{feature_set} unexpectedly includes {name}",
                )

    def test_options_variant_keeps_call_activity(self) -> None:
        columns = feature_columns("daily_technical_options")
        self.assertIn("rank_call_volume", columns)
        self.assertIn("rank_call_volume_prior20_zscore", columns)
        self.assertIn("option_available", columns)

    def test_technical_baseline_has_no_option_columns(self) -> None:
        columns = feature_columns("daily_technical")
        self.assertFalse(any("call_" in column for column in columns))
        self.assertNotIn("option_available", columns)


if __name__ == "__main__":
    unittest.main()
