from __future__ import annotations

import csv
import gzip
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from alientai_v2.research.us_smallcap_range_volume_clone import (
    MODEL_ID,
    NASDAQ_MODEL_ID,
    SOURCE_MODEL_ID,
    active_stock_symbols,
    score_candidates,
    screen_universe,
    sha256,
    validate_clone_contract,
)


def technical(symbol: str, **changes: object) -> dict[str, object]:
    row: dict[str, object] = {
        "symbol": symbol,
        "provider": "Schwab",
        "available_at_utc": "2026-08-07T20:15:00+00:00",
        "market_date": "2026-08-07",
        "close": 20.0,
        "technical_latest_relative_volume_20": 2.0,
        "technical_atr14_pct": 3.0,
        "technical_ema_bullish_alignment": True,
        "technical_ema9_distance_pct": 1.0,
        "technical_ema21_distance_pct": 2.0,
        "technical_ema50_distance_pct": 3.0,
        "technical_rsi_14": 55.0,
    }
    row.update(changes)
    return row


def market_cap(symbol: str, value: float = 1_000_000_000.0) -> dict[str, object]:
    return {
        "symbol": symbol,
        "provider": "Schwab",
        "available_at_utc": "2026-08-07T20:15:00+00:00",
        "market_cap_usd": value,
    }


class FakeModel:
    best_iteration = 1

    def predict(self, matrix: np.ndarray, num_iteration: int) -> np.ndarray:
        del num_iteration
        return matrix[:, 0] / 100.0


class SmallCapRangeVolumeCloneTests(unittest.TestCase):
    def test_listing_starts_with_all_exchanges_and_excludes_etfs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "listing.csv.gz"
            with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "symbol",
                        "exchange",
                        "assetType",
                        "status",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "symbol": "NAS",
                            "exchange": "NASDAQ",
                            "assetType": "Stock",
                            "status": "Active",
                        },
                        {
                            "symbol": "NYS",
                            "exchange": "NYSE",
                            "assetType": "Stock",
                            "status": "Active",
                        },
                        {
                            "symbol": "AME",
                            "exchange": "AMEX",
                            "assetType": "Stock",
                            "status": "Active",
                        },
                        {
                            "symbol": "ETF",
                            "exchange": "NYSE ARCA",
                            "assetType": "ETF",
                            "status": "Active",
                        },
                    ]
                )
            self.assertEqual(["AME", "NAS", "NYS"], active_stock_symbols(path))
            self.assertEqual(
                ["NAS"],
                active_stock_symbols(path, allowed_exchanges=["NASDAQ"]),
            )

    def test_screen_requires_every_declared_rule(self) -> None:
        names = ["PASS", "CAP", "PRICE", "RV", "TREND", "RANGE"]
        rows = [
            technical("PASS"),
            technical("CAP"),
            technical("PRICE", close=50.0),
            technical("RV", technical_latest_relative_volume_20=1.99),
            technical("TREND", technical_ema_bullish_alignment=False),
            technical("RANGE", technical_atr14_pct=2.99),
        ]
        caps = [market_cap(name) for name in names]
        caps[1] = market_cap("CAP", 2_000_000_000.0)
        eligible, counts = screen_universe(
            names,
            rows,
            caps,
            decision_date="2026-08-07",
            cutoff_utc=datetime(2026, 8, 7, 20, 30, tzinfo=timezone.utc),
            provider="Schwab",
            maximum_market_cap_usd=2_000_000_000.0,
            maximum_price_usd=50.0,
            minimum_relative_volume_20=2.0,
            minimum_atr14_pct=3.0,
        )
        self.assertEqual(["PASS"], [row["symbol"] for row in eligible])
        self.assertEqual(1, counts["market_cap_rejected"])
        self.assertEqual(1, counts["price_rejected"])
        self.assertEqual(1, counts["relative_volume_rejected"])
        self.assertEqual(1, counts["uptrend_rejected"])
        self.assertEqual(1, counts["range_rejected"])

    def test_screen_rejects_late_or_mixed_provider_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "provider"):
            screen_universe(
                ["ABC"],
                [technical("ABC", provider="Alpha Vantage")],
                [market_cap("ABC")],
                decision_date="2026-08-07",
                cutoff_utc=datetime(2026, 8, 7, 20, 30, tzinfo=timezone.utc),
                provider="Schwab",
                maximum_market_cap_usd=2_000_000_000.0,
                maximum_price_usd=50.0,
                minimum_relative_volume_20=2.0,
                minimum_atr14_pct=3.0,
            )
        with self.assertRaisesRegex(ValueError, "after the decision cutoff"):
            screen_universe(
                ["ABC"],
                [technical("ABC", available_at_utc="2026-08-07T20:31:00Z")],
                [market_cap("ABC")],
                decision_date="2026-08-07",
                cutoff_utc=datetime(2026, 8, 7, 20, 30, tzinfo=timezone.utc),
                provider="Schwab",
                maximum_market_cap_usd=2_000_000_000.0,
                maximum_price_usd=50.0,
                minimum_relative_volume_20=2.0,
                minimum_atr14_pct=3.0,
            )

    def test_clone_hashes_and_selection_cap_are_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model_path = root / "model.txt"
            report_path = root / "report.json"
            model_path.write_text("model", encoding="utf-8")
            report_path.write_text("{}", encoding="utf-8")
            contract = {
                "model_id": MODEL_ID,
                "source_model_id": SOURCE_MODEL_ID,
                "horizon_sessions": 5,
                "round_trip_cost_pct": 0.25,
                "source_artifacts": {
                    "model_sha256": sha256(model_path),
                    "report_sha256": sha256(report_path),
                },
            }
            validate_clone_contract(
                contract,
                model_path=model_path,
                report_path=report_path,
            )
            contract["model_id"] = NASDAQ_MODEL_ID
            validate_clone_contract(
                contract,
                model_path=model_path,
                report_path=report_path,
            )
            rows = [
                {"symbol": f"T{i}", "technical_rsi_14": 90.0 - i}
                for i in range(8)
            ]
            scored, selected = score_candidates(
                rows,
                model=FakeModel(),
                feature_names=["technical_rsi_14"],
                score_cutoff=0.0,
                maximum_selections=5,
            )
            self.assertEqual(8, len(scored))
            self.assertEqual(5, len(selected))
            self.assertEqual("T0", selected[0]["symbol"])


if __name__ == "__main__":
    unittest.main()
