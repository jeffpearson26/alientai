import unittest

from create_v2_transformer_2day_sp500_trainer import build_two_day_source
from test_transformer_5day_isolation import SOURCE_FIXTURE


class TransformerTwoDayIsolationTests(unittest.TestCase):
    def setUp(self):
        self.result = build_two_day_source(SOURCE_FIXTURE)

    def test_isolates_build_output_and_artifacts(self):
        self.assertIn("TRANSFORMER_2DAY_SP500", self.result)
        self.assertIn("transformer_2day_sp500_supabase_training", self.result)
        for name in ("model.pt", "scaler.json", "metrics.json", "symbol_summary.json", "config.json"):
            self.assertIn(f"transformer_2day_sp500_{name}", self.result)

    def test_freezes_two_day_research_defaults(self):
        self.assertIn('"--horizon-days", type=int, default=2', self.result)
        self.assertIn('"--step-days", type=int, default=1', self.result)
        self.assertIn('"--split-embargo-calendar-days", type=int, default=12', self.result)
        self.assertIn('"--non-overlapping-calendar-days", type=int, default=4', self.result)
        self.assertIn("if args.horizon_days != 2", self.result)


if __name__ == "__main__":
    unittest.main()
