from __future__ import annotations

import unittest

from score_natural_technical_context import score_rows


class FakeModel:
    def predict(self, values):
        return [float(row[0]) / 100.0 for row in values]


class ScoreNaturalTechnicalContextTests(unittest.TestCase):
    def test_scores_rows_and_preserves_research_only_flag(self) -> None:
        result = score_rows([{"technical_rsi_2": 20.0}], ["technical_rsi_2"], FakeModel())
        self.assertEqual(result[0]["technical_context_score"], 0.2)
        self.assertTrue(result[0]["research_only"])

    def test_missing_model_feature_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing required"):
            score_rows([{"technical_rsi_2": 20.0}], ["technical_atr14_pct"], FakeModel())


if __name__ == "__main__":
    unittest.main()
