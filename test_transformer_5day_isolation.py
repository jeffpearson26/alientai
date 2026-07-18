import unittest

from create_v2_transformer_5day_sp500_trainer import build_five_day_source


SOURCE_FIXTURE = '''
BUILD = "ALIENTAI_V2_TRANSFORMER_20DAY_SP500_SUPABASE_TRAINER_V1"
OUT_DIR = PROJECT_ROOT / "data_v2" / "transformer_20day_sp500_supabase_training"
parser = argparse.ArgumentParser(description="Train V2 20-day daily transformer model.")
parser.add_argument("--horizon-days", type=int, default=20)
parser.add_argument("--step-days", type=int, default=5)
parser.add_argument("--split-embargo-calendar-days", type=int, default=32)
parser.add_argument("--checkpoint-threshold", type=float, default=0.60)
parser.add_argument("--checkpoint-minimum-signals", type=int, default=500)
parser.add_argument("--non-overlapping-calendar-days", type=int, default=28)
    args = parser.parse_args()

    random.seed(args.seed)
model_path = OUT_DIR / "transformer_20day_sp500_model.pt"
scaler_path = OUT_DIR / "transformer_20day_sp500_scaler.json"
metrics_path = OUT_DIR / "transformer_20day_sp500_metrics.json"
symbol_summary_path = OUT_DIR / "transformer_20day_sp500_symbol_summary.json"
config_path = OUT_DIR / "transformer_20day_sp500_config.json"
'''


class TransformerFiveDayIsolationTests(unittest.TestCase):
    def setUp(self):
        self.result = build_five_day_source(SOURCE_FIXTURE)

    def test_uses_isolated_build_and_output_directory(self):
        self.assertIn("TRANSFORMER_5DAY_SP500", self.result)
        self.assertIn("transformer_5day_sp500_supabase_training", self.result)
        self.assertNotIn("TRANSFORMER_20DAY_SP500", self.result)

    def test_all_model_artifacts_are_isolated(self):
        for name in ("model.pt", "scaler.json", "metrics.json", "symbol_summary.json", "config.json"):
            self.assertIn(f"transformer_5day_sp500_{name}", self.result)
        self.assertNotIn("transformer_20day_sp500_model.pt", self.result)

    def test_defaults_match_five_day_research_design(self):
        self.assertIn('"--horizon-days", type=int, default=5', self.result)
        self.assertIn('"--step-days", type=int, default=2', self.result)
        self.assertIn('"--split-embargo-calendar-days", type=int, default=12', self.result)
        self.assertIn('"--non-overlapping-calendar-days", type=int, default=9', self.result)
        self.assertIn('"--checkpoint-threshold", type=float, default=0.55', self.result)
        self.assertIn('"--checkpoint-minimum-signals", type=int, default=1000', self.result)

    def test_rejects_non_five_day_horizon(self):
        self.assertIn("if args.horizon_days != 5", self.result)

    def test_source_transformer_architecture_is_preserved(self):
        original = SOURCE_FIXTURE + "\nclass TimeSeriesTransformer: pass\n"
        result = build_five_day_source(original)
        self.assertIn("class TimeSeriesTransformer", result)


if __name__ == "__main__":
    unittest.main()
