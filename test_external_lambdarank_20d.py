from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from alientai_v2.research.external_lambdarank_20d import (
    CONTEXT_SYMBOL,
    FEATURE_COLUMNS,
    HORIZON_SESSIONS,
    MINIMUM_CANDIDATES,
    ROUND_TRIP_COST_PCT,
    UNTRUSTED_JOBLIB_SHA256,
    build_panels,
    purged_folds,
    resolve_symbol_file,
    select_latest,
    schwab_date_offset_days,
)


def synthetic_daily():
    symbols = [f"S{index:03d}" for index in range(MINIMUM_CANDIDATES)]
    # Leave enough whole dates for five validation blocks plus an exact
    # 20-session purge/embargo on both sides of the middle folds.
    dates = pd.bdate_range("2024-07-01", periods=260)
    daily = {}
    for symbol_index, symbol in enumerate([*symbols, CONTEXT_SYMBOL]):
        rows = []
        slope = 0.08 + symbol_index * 0.0008
        for date_index, date in enumerate(dates):
            close = 40.0 + symbol_index * 0.03 + slope * date_index
            open_price = close * (1.0 - 0.001 + symbol_index * 0.000001)
            rows.append(
                {
                    "symbol": symbol,
                    "market_date": date.date().isoformat(),
                    "open": open_price,
                    "high": max(open_price, close) * 1.01,
                    "low": min(open_price, close) * 0.99,
                    "close": close,
                    "volume": 1_000_000.0 + symbol_index * 1_000 + date_index,
                }
            )
        daily[symbol] = rows
    return symbols, daily


class ExternalLambdaRankPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.symbols, cls.daily = synthetic_daily()
        cls.result = build_panels(cls.daily, cls.symbols)

    def test_full_candidate_coverage_is_required(self) -> None:
        self.assertEqual(
            self.result.feature_panel.groupby("market_date")["symbol"]
            .nunique()
            .min(),
            MINIMUM_CANDIDATES,
        )
        broken = dict(self.daily)
        broken.pop(self.symbols[-1])
        with self.assertRaisesRegex(ValueError, "daily keys"):
            build_panels(broken, self.symbols)

    def test_source_roots_are_strict_priority_fallbacks(self) -> None:
        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            primary = base / "primary"
            fallback = base / "fallback"
            primary.mkdir()
            fallback.mkdir()
            primary_file = primary / "AAPL_schwab_1d_max.csv"
            fallback_file = fallback / "AAPL_schwab_1d_max.csv"
            primary_file.touch()
            fallback_file.touch()
            self.assertEqual(
                resolve_symbol_file("AAPL", [primary, fallback]),
                primary_file.resolve(),
            )

    def test_schwab_date_mapping_is_schema_specific(self) -> None:
        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            stored_session = base / "stored_session.csv"
            pacific_key = base / "pacific_key.csv"
            stored_session.write_text(
                "symbol,datetime_ms,datetime_utc,date,open,high,low,close,volume\n",
                encoding="utf-8",
            )
            pacific_key.write_text(
                "symbol,schwab_symbol,date,datetime,open,high,low,close,volume\n",
                encoding="utf-8",
            )
            self.assertEqual(schwab_date_offset_days(stored_session), 0)
            self.assertEqual(schwab_date_offset_days(pacific_key), 1)

    def test_label_uses_next_open_and_twentieth_close(self) -> None:
        row = self.result.labeled_panel.iloc[0]
        symbol = str(row["symbol"])
        candles = self.daily[symbol]
        positions = {
            candle["market_date"]: index
            for index, candle in enumerate(candles)
        }
        decision_index = positions[str(row["market_date"])]
        expected_entry = candles[decision_index + 1]
        expected_exit = candles[decision_index + HORIZON_SESSIONS]
        expected_net = (
            expected_exit["close"] / expected_entry["open"] - 1.0
        ) * 100.0 - ROUND_TRIP_COST_PCT
        self.assertEqual(
            row["label_entry_date"], expected_entry["market_date"]
        )
        self.assertEqual(
            row["label_exit_date"], expected_exit["market_date"]
        )
        self.assertAlmostEqual(
            float(row["label_net_return_pct"]), expected_net, places=10
        )

    def test_relevance_has_five_real_buckets(self) -> None:
        by_date = self.result.labeled_panel.groupby("market_date")[
            "relevance"
        ].apply(lambda values: set(values.astype(int)))
        self.assertTrue(all(values == {0, 1, 2, 3, 4} for values in by_date))

    def test_features_are_same_shared_contract(self) -> None:
        self.assertFalse(
            self.result.feature_panel[list(FEATURE_COLUMNS)].isna().any().any()
        )
        self.assertEqual(len(FEATURE_COLUMNS), 13)
        self.assertTrue(
            np.allclose(
                self.result.feature_panel["rank_ret_10d"],
                self.result.feature_panel["rank_roc_10"],
            )
        )

    def test_purged_folds_have_no_label_overlap(self) -> None:
        frame = self.result.labeled_panel
        folds = purged_folds(frame, n_splits=5)
        self.assertEqual(len(folds), 5)
        date_rows = frame[
            ["market_date", "label_entry_date", "label_exit_date"]
        ].drop_duplicates()
        for fold in folds:
            validation = date_rows[
                date_rows["market_date"].isin(fold.validation_dates)
            ]
            train = date_rows[date_rows["market_date"].isin(fold.train_dates)]
            interval_start = validation["market_date"].min()
            interval_end = validation["label_exit_date"].max()
            overlap = (
                (train["label_entry_date"] <= interval_end)
                & (train["label_exit_date"] >= interval_start)
            )
            self.assertFalse(overlap.any())
            self.assertTrue(
                set(fold.train_dates).isdisjoint(fold.embargo_dates)
            )

    def test_latest_selection_is_bounded_and_deterministic(self) -> None:
        latest = self.result.feature_panel[
            self.result.feature_panel["market_date"]
            == self.result.feature_panel["market_date"].max()
        ].copy()
        latest["model_score"] = np.arange(len(latest), dtype=float)
        selected = select_latest(latest, maximum_selections=10)
        self.assertEqual(len(selected), 10)
        self.assertTrue(selected["model_score"].is_monotonic_decreasing)

    def test_untrusted_joblib_is_explicitly_quarantined(self) -> None:
        self.assertEqual(
            UNTRUSTED_JOBLIB_SHA256,
            "44ad9f72ed26f749c759977fba082e5d7ca656cc36b5d71e7b75b345534c1e91",
        )


if __name__ == "__main__":
    unittest.main()
