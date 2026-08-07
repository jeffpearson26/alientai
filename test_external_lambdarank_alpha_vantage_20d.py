from __future__ import annotations

import unittest

import pandas as pd

from alientai_v2.research.external_lambdarank_alpha_vantage_20d import (
    EMBARGO_SESSIONS,
    MODEL_ID,
    _point_in_time_volume,
    _valid_adjusted_values,
    chronological_panel_split,
)


class ExternalLambdaRankAlphaVantageTests(unittest.TestCase):
    def test_model_identity_is_source_specific(self) -> None:
        self.assertIn("alpha_vantage", MODEL_ID)
        self.assertNotIn("corrected_v2", MODEL_ID)

    def test_chronological_split_purges_and_embargoes_boundary(self) -> None:
        dates = pd.bdate_range("2025-01-02", periods=260)
        rows = []
        for index, market_date in enumerate(dates[:-20]):
            rows.append(
                {
                    "market_date": market_date.date().isoformat(),
                    "symbol": "AAA",
                    "label_exit_date": dates[index + 20].date().isoformat(),
                }
            )
        frame = pd.DataFrame(rows)
        development, sealed, details = chronological_panel_split(frame)
        self.assertEqual(
            details["boundary_embargo_sessions"], EMBARGO_SESSIONS
        )
        self.assertLess(
            development["label_exit_date"].max(),
            sealed["market_date"].min(),
        )
        self.assertTrue(
            set(development["market_date"]).isdisjoint(
                set(sealed["market_date"])
            )
        )
        self.assertEqual(
            len(details["boundary_embargo_dates"]), EMBARGO_SESSIONS
        )

    def test_adjusted_envelope_allows_machine_precision_rounding(self) -> None:
        self.assertTrue(
            _valid_adjusted_values(
                {
                    "open": 30.050607096280288,
                    "high": 30.242575079150463,
                    "low": 28.9841183025571,
                    "close": 28.984118302557096,
                    "volume": 36_744_600.0,
                }
            )
        )

    def test_volume_does_not_use_a_future_split_factor(self) -> None:
        self.assertEqual(
            _point_in_time_volume(
                {"6. volume": "1000", "8. split coefficient": "4.0"}
            ),
            1000.0,
        )


if __name__ == "__main__":
    unittest.main()
