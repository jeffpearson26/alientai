from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from alientai_v2.research.long_horizon_technicals import (
    long_horizon_technical_features,
)
from build_nasdaq101_126session_technical_panel import build_rows
from train_nasdaq101_126session_technical_model import (
    add_cross_sectional_feature_ranks,
    add_qqq_relative_targets,
    additive_mark_to_market_drawdown,
    cross_sectional_score_percentiles,
    nonoverlap_summary,
    split_dates,
)
from score_nasdaq101_126session_technical_model import latest_rows


def candles(count: int = 420, offset: float = 0.0) -> list[dict]:
    start = date(2020, 1, 1)
    rows = []
    for index in range(count):
        close = 100.0 + offset + index * 0.10 + np.sin(index / 8.0)
        rows.append(
            {
                "market_date": str(start + timedelta(days=index)),
                "open": close - 0.10,
                "high": close + 0.50,
                "low": close - 0.50,
                "close": close,
                "volume": 1_000_000.0 + index * 100.0,
                "adjustment_factor": 1.0,
            }
        )
    return rows


def test_features_are_point_in_time_and_include_long_windows() -> None:
    full = candles(420)
    first = long_horizon_technical_features(full[:300])
    mutated = [dict(row) for row in full]
    for row in mutated[300:]:
        row["close"] *= 100.0
    second = long_horizon_technical_features(mutated[:300])
    assert first == second
    assert first["lh_return_126d_pct"] is not None
    assert first["lh_slope_252_pct_per_day"] is not None
    assert first["lh_money_flow_index_14"] is not None
    assert first["lh_chaikin_money_flow_20d"] is not None


def test_panel_uses_candidates_only_and_exact_126_session_label() -> None:
    candidate = candles(offset=2.0)
    daily = {
        "AAA": candidate,
        "QQQ": candles(offset=1.0),
        "SPY": candles(),
    }
    rows = build_rows(daily, ["AAA"], "2020-01-01")
    first = rows[0]
    decision_index = 125
    assert {row["symbol"] for row in rows} == {"AAA"}
    assert first["market_date"] == candidate[decision_index]["market_date"]
    assert (
        first["label_entry_market_date"]
        == candidate[decision_index + 1]["market_date"]
    )
    assert (
        first["label_126d_exit_market_date"]
        == candidate[decision_index + 126]["market_date"]
    )
    expected = (
        candidate[decision_index + 126]["close"]
        / candidate[decision_index + 1]["open"]
        - 1.0
    ) * 100.0
    assert first["label_126d_gross_return_pct"] == pytest.approx(expected)
    assert first["label_126d_net_return_pct"] == pytest.approx(expected - 0.25)
    assert "qqq_lh_return_126d_pct" in first
    assert "spy_lh_return_126d_pct" in first
    assert "relative_to_qqq_126d_pct" in first


def test_split_uses_126_session_two_sided_embargoes() -> None:
    start = date(2000, 1, 1)
    dates = [str(start + timedelta(days=index)) for index in range(5000)]
    splits = split_dates(dates)
    ordered = sorted(dates)
    names = (
        "train",
        "fit_validation",
        "calibration",
        "policy_validation",
        "test",
    )
    for left, right in zip(names, names[1:]):
        gap = ordered.index(min(splits[right])) - ordered.index(
            max(splits[left])
        ) - 1
        assert gap >= 126


def test_nonoverlap_uses_market_calendar_not_selected_date_order() -> None:
    rows = [
        {
            "market_date": str(date(2020, 1, 1) + timedelta(days=index * 7)),
            "market_session_index": index * 126,
            "label_126d_net_return_pct": 1.0,
        }
        for index in range(5)
    ]
    summary = nonoverlap_summary(rows)
    assert summary["observed_folds"] == 1
    assert summary["folds"][0]["signals"] == 5


def test_drawdown_respects_idle_cash_and_daily_marking() -> None:
    source = candles(260)
    entry_index = 1
    exit_index = 126
    row = {
        "symbol": "AAA",
        "label_entry_market_date": source[entry_index]["market_date"],
        "label_entry_next_adjusted_open": source[entry_index]["open"],
        "label_126d_exit_market_date": source[exit_index]["market_date"],
        "round_trip_cost_pct": 0.25,
    }
    drawdown = additive_mark_to_market_drawdown([row], {"AAA": source})
    assert drawdown is not None
    assert drawdown > -0.1


def test_current_scorer_keeps_benchmarks_context_only() -> None:
    daily = {
        "AAA": candles(offset=2.0),
        "QQQ": candles(offset=1.0),
        "SPY": candles(),
    }
    decision_date, rows = latest_rows(daily, ["AAA"])
    assert decision_date == daily["QQQ"][-1]["market_date"]
    assert [row["symbol"] for row in rows] == ["AAA"]
    assert "qqq_lh_return_126d_pct" in rows[0]
    assert "spy_lh_return_126d_pct" in rows[0]


def test_cross_sectional_ranking_is_date_local() -> None:
    rows = [
        {
            "market_date": market_date,
            "symbol": symbol,
            "lh_return_126d_pct": value,
        }
        for market_date, values in (
            ("2020-01-01", (1.0, 2.0, 3.0)),
            ("2020-01-02", (100.0, 200.0, 300.0)),
        )
        for symbol, value in zip(("A", "B", "C"), values)
    ]
    names = add_cross_sectional_feature_ranks(rows)
    assert "rank_lh_return_126d_pct" in names
    assert [row["rank_lh_return_126d_pct"] for row in rows[:3]] == [
        0.0,
        0.5,
        1.0,
    ]
    scores = cross_sectional_score_percentiles(
        rows, np.asarray([1, 2, 3, 30, 20, 10], dtype=float)
    )
    assert scores.tolist() == [0.0, 0.5, 1.0, 1.0, 0.5, 0.0]


def test_model_target_is_future_excess_return_over_qqq() -> None:
    qqq = candles(260)
    row = {
        "label_entry_market_date": qqq[1]["market_date"],
        "label_126d_exit_market_date": qqq[126]["market_date"],
        "label_126d_gross_return_pct": 20.0,
    }
    add_qqq_relative_targets([row], qqq)
    qqq_gross = (qqq[126]["close"] / qqq[1]["open"] - 1.0) * 100.0
    assert row["model_qqq_126d_gross_return_pct"] == pytest.approx(qqq_gross)
    assert row["model_excess_to_qqq_126d_pct"] == pytest.approx(
        20.0 - qqq_gross
    )
