import unittest

from train_v2_transformer_20day_russell_from_supabase import make_symbol_windows


class RussellTransformerContinuityTests(unittest.TestCase):
    def test_rejects_a_long_gap_inside_feature_or_horizon_window(self):
        day_ms = 86_400_000
        candles = []
        for index in range(700):
            close = 100.0 + index
            timestamp = (index + 1) * day_ms + (365 * day_ms if index >= 263 else 0)
            candles.append({
                "date": f"d{index}", "datetime_ms": timestamp,
                "open": close - 0.5, "high": close + 1.0, "low": close - 1.0,
                "close": close, "volume": 1_000 + index,
            })
        _, _, _, metadata = make_symbol_windows(
            symbol="TEST", candles=candles, sequence_length=60, horizon_days=20,
            min_history_days=220, step_days=1,
        )
        self.assertTrue(metadata)
        self.assertNotIn(candles[243]["datetime_ms"], [row["datetime_ms"] for row in metadata])


if __name__ == "__main__":
    unittest.main()
