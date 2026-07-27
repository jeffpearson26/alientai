import unittest

from create_v2_transformer_2day_russell_trainer import build_russell_source


SOURCE_FIXTURE = '''
BUILD = "ALIENTAI_V2_TRANSFORMER_2DAY_SP500_SUPABASE_TRAINER_V1"
OUT_DIR = PROJECT_ROOT / "data_v2" / "transformer_2day_sp500_supabase_training"
parser = argparse.ArgumentParser(description="Train isolated V2 two-day daily Transformer model.")
model_path = OUT_DIR / "transformer_2day_sp500_model.pt"
scaler_path = OUT_DIR / "transformer_2day_sp500_scaler.json"
metrics_path = OUT_DIR / "transformer_2day_sp500_metrics.json"
symbol_summary_path = OUT_DIR / "transformer_2day_sp500_symbol_summary.json"
config_path = OUT_DIR / "transformer_2day_sp500_config.json"
'''


class TransformerTwoDayRussellIsolationTests(unittest.TestCase):
    def test_isolates_russell_build_output_and_artifacts(self):
        result = build_russell_source(SOURCE_FIXTURE)
        self.assertIn("TRANSFORMER_2DAY_RUSSELL", result)
        self.assertIn("transformer_2day_russell_supabase_training", result)
        self.assertNotIn("transformer_2day_sp500_model.pt", result)
        for name in ("model.pt", "scaler.json", "metrics.json", "symbol_summary.json", "config.json"):
            self.assertIn(f"transformer_2day_russell_{name}", result)


if __name__ == "__main__":
    unittest.main()
