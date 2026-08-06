from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from alientai_v2.research.cross_sectional_picker_5d import (
    LABEL_EXIT_DATE,
    add_feature_ranks,
    build_daily_snapshot,
    evaluate_predictions,
    passes_configured_filters,
    purged_date_folds,
    ranked_feature_names,
)
from alientai_v2.research.cross_sectional_technical_5d import (
    RANK_FEATURES,
    technical_features,
)


def candles(count: int = 100, drift: float = 0.10) -> list[dict]:
    start = date(2025, 1, 1)
    rows = []
    for index in range(count):
        close = 100.0 + drift * index + np.sin(index / 5.0)
        rows.append(
            {
                "market_date": str(start + timedelta(days=index)),
                "open": close - 0.05,
                "high": close + 0.50,
                "low": close - 0.50,
                "close": close,
                "volume": 1_000_000.0 + 2_000.0 * index,
            }
        )
    return rows


def test_model_inputs_are_all_cross_sectional_ranks() -> None:
    names = ranked_feature_names()
    assert len(names) == len(RANK_FEATURES)
    assert all(name.startswith("rank_") for name in names)
    assert not any("label" in name or "future" in name for name in names)


def test_snapshot_ranking_is_label_free_and_date_local() -> None:
    rows, coverage = build_daily_snapshot(
        {
            "AAA": candles(drift=0.06),
            "BBB": candles(drift=0.12),
            "CCC": candles(drift=0.18),
            "QQQ": candles(drift=0.10),
            "SPY": candles(drift=0.08),
        },
        ["AAA", "BBB", "CCC"],
        as_of_date=None,
        minimum_cross_sectional_coverage=1.0,
    )
    assert coverage["available_count"] == 3
    assert not any(
        key.startswith("label_") for row in rows for key in row
    )
    spanning_features = 0
    for name in ranked_feature_names():
        values = [row[name] for row in rows if row[name] is not None]
        assert all(0.0 <= value <= 1.0 for value in values)
        if min(values) == 0.0 and max(values) == 1.0:
            spanning_features += 1
        else:
            assert set(values) == {0.5}
    assert spanning_features > 0


def test_feature_ranker_does_not_require_a_target() -> None:
    rows = []
    for index, symbol in enumerate(("AAA", "BBB", "CCC")):
        features = technical_features(candles(drift=0.05 + index * 0.05))
        rows.append(
            {
                "symbol": symbol,
                "market_date": "2026-01-02",
                **features,
            }
        )
    add_feature_ranks(rows)
    assert rows[-1]["rank_x5_return_10d_pct"] == 1.0
    assert all("label_5d_net_return_pct" not in row for row in rows)


def test_configured_filters_include_relative_volume() -> None:
    row = {
        **technical_features(candles()),
        "x5_eligible": True,
    }
    filters = {
        "minimum_price": 5.0,
        "minimum_average_dollar_volume": 20_000_000.0,
        "minimum_relative_volume": 0.75,
        "maximum_atr_pct": 10.0,
    }
    row["x5_relative_volume_20d"] = 0.50
    assert not passes_configured_filters(row, filters)
    row["x5_relative_volume_20d"] = 1.0
    assert passes_configured_filters(row, filters)


def test_purged_folds_remove_overlap_and_apply_post_fold_embargo() -> None:
    dates = [
        str(date(2024, 1, 1) + timedelta(days=index))
        for index in range(180)
    ]
    rows = [
        {
            "market_date": dates[index],
            LABEL_EXIT_DATE: dates[index + 5],
        }
        for index in range(len(dates) - 5)
    ]
    exits = {row["market_date"]: row[LABEL_EXIT_DATE] for row in rows}
    folds = purged_date_folds(rows, n_splits=5, embargo_sessions=5)
    assert len(folds) == 5
    for fold in folds:
        train = set(fold.train_dates)
        test = set(fold.test_dates)
        assert train.isdisjoint(test)
        assert train.isdisjoint(fold.embargo_dates)
        for train_date in train:
            if train_date < fold.test_dates[0]:
                assert exits[train_date] < fold.test_dates[0]


def test_evaluation_reports_ic_hit_rate_and_real_portfolio_path() -> None:
    rows = []
    scores = []
    start = date(2025, 1, 1)
    for day in range(30):
        decision_date = str(start + timedelta(days=day))
        for rank in range(10):
            net = float(rank - 4) / 10.0
            row = {
                "symbol": f"S{rank:02d}",
                "market_date": decision_date,
                "label_5d_cross_sectional_return_rank": rank / 9.0,
                "label_5d_net_return_pct": net,
                "label_5d_exit_market_date": str(
                    start + timedelta(days=day + 5)
                ),
                "round_trip_cost_pct": 0.25,
                "x5_atr_14_pct": 2.0,
                "label_5d_mark_to_market_path": [
                    {
                        "market_date": str(
                            start + timedelta(days=day + step + 1)
                        ),
                        "gross_return_from_entry_pct": (
                            (net + 0.25) * (step + 1) / 5.0
                        ),
                    }
                    for step in range(5)
                ],
            }
            rows.append(row)
            scores.append(float(rank))
    result, selected = evaluate_predictions(
        rows,
        np.asarray(scores),
        top_quantile=0.20,
        maximum_names=2,
        horizon_sessions=5,
        weighting="equal",
    )
    assert result["rank_information_coefficient"]["mean_spearman"] > 0.99
    assert result["top_basket"]["signals"] == 60
    assert result["top_basket"]["hit_rate"] == 1.0
    assert result["top_minus_bottom_mean_net_pct"] > 0.0
    assert result["long_only_portfolio"]["total_return_pct"] > 0.0
    assert len(selected) == 60
