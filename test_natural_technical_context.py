from __future__ import annotations

import unittest

from train_natural_technical_context import chronological_split, technical_feature_names


def row(day: str, rsi: float, future_return: float) -> dict[str, object]:
    return {"market_date": day, "technical_rsi_2": rsi, "technical_constant": 1.0,
            "label_forward_return_5d_pct": future_return}


class NaturalTechnicalContextTests(unittest.TestCase):
    def test_only_varying_technical_fields_are_features(self) -> None:
        rows = [row("2026-01-01", 10.0, 1.0), row("2026-01-02", 20.0, 2.0)]
        self.assertEqual(technical_feature_names(rows), ["technical_rsi_2"])

    def test_split_is_chronological_and_embargoes_middle_boundary(self) -> None:
        rows = [row(f"2026-01-{day:02d}", float(day), 1.0) for day in range(1, 31)]
        train, validation, test, split = chronological_split(rows, 0.50, 0.25, 2)
        self.assertLess(max(train), min(validation))
        self.assertLess(max(validation), min(test))
        self.assertEqual(split["validation_start"], "2026-01-17")
        self.assertEqual(split["test_start"], "2026-01-24")


if __name__ == "__main__":
    unittest.main()
