from __future__ import annotations

from datetime import date, timedelta
import json

import numpy as np

from alientai_v2.research.cross_sectional_technical_5d import (
    TRANSPARENT_WEIGHTS,
    add_date_local_ranks,
    eligibility,
    technical_features,
)
from build_cross_sectional_technical_5d_panel import (
    build_rows,
    validate_manifest,
)
from train_cross_sectional_technical_5d import (
    mark_to_market_drawdown,
    policy_gate,
    select_rows,
    split_dates,
)


def candles(count: int = 90, drift: float = 0.1) -> list[dict]:
    start = date(2025, 1, 1)
    rows = []
    for index in range(count):
        close = 100.0 + drift * index + np.sin(index / 4.0)
        rows.append(
            {
                "market_date": str(start + timedelta(days=index)),
                "open": close - 0.05,
                "high": close + 0.50,
                "low": close - 0.50,
                "close": close,
                "volume": 1_000_000.0 + index * 1_000.0,
            }
        )
    return rows


def test_features_use_only_candles_through_decision() -> None:
    original = candles()
    first = technical_features(original[:70])
    mutated = [dict(row) for row in original]
    for row in mutated[70:]:
        row["close"] *= 100.0
    second = technical_features(mutated[:70])
    assert first == second
    assert first["x5_return_5d_pct"] is not None
    assert first["x5_adx_14"] is not None


def test_transparent_score_uses_supplied_weights_and_date_local_ranks() -> None:
    rows = []
    for index, symbol in enumerate(("AAA", "BBB", "CCC")):
        row = {
            "symbol": symbol,
            "market_date": "2026-01-02",
            "label_5d_net_return_pct": float(index),
        }
        for source in {name.removeprefix("rank_") for name in TRANSPARENT_WEIGHTS}:
            row[source] = float(index)
        # The ranker also requires its remaining declared feature family.
        template = technical_features(candles(drift=0.05 + index * 0.02))
        for name, value in template.items():
            row.setdefault(name, value)
        rows.append(row)
    add_date_local_ranks(rows)
    assert rows[0]["x5_transparent_composite_score"] == 0.0
    assert rows[-1]["x5_transparent_composite_score"] == 1.0
    assert rows[-1]["label_5d_cross_sectional_return_rank"] == 1.0


def test_eligibility_fails_low_liquidity_and_excessive_gap() -> None:
    features = technical_features(candles())
    features["x5_average_dollar_volume_20d"] = 1_000.0
    features["x5_gap_1d_pct"] = 12.0
    passed, failures = eligibility(features)
    assert not passed
    assert {"liquidity", "gap_cap"}.issubset(failures)


def test_panel_label_is_next_open_to_fifth_subsequent_close() -> None:
    common = candles(100)
    daily = {
        "AAA": common,
        "BBB": candles(100, drift=0.12),
        "QQQ": candles(100, drift=0.08),
        "SPY": candles(100, drift=0.06),
    }
    rows, _ = build_rows(
        daily,
        ["AAA", "BBB"],
        start_date="2025-01-01",
        minimum_cross_sectional_coverage=1.0,
    )
    row = rows[0]
    decision_index = 59
    assert row["market_date"] == common[decision_index]["market_date"]
    assert (
        row["label_entry_market_date"]
        == common[decision_index + 1]["market_date"]
    )
    assert (
        row["label_5d_exit_market_date"]
        == common[decision_index + 5]["market_date"]
    )
    expected = (
        common[decision_index + 5]["close"]
        / common[decision_index + 1]["open"]
        - 1.0
    ) * 100.0 - 0.25
    assert np.isclose(row["label_5d_net_return_pct"], expected)
    assert len(row["label_5d_mark_to_market_path"]) == 5


def test_manifest_rejects_unadjusted_supplement(tmp_path) -> None:
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "status": "complete",
                "completed": ["ANET"],
                "failed": {},
                "function": "TIME_SERIES_DAILY",
                "outputsize": "full",
            }
        ),
        encoding="utf-8",
    )
    try:
        validate_manifest(tmp_path, ["ANET"])
    except ValueError as error:
        assert "not full adjusted daily" in str(error)
    else:
        raise AssertionError("unadjusted manifest should fail closed")


def test_split_has_two_sided_five_session_embargoes() -> None:
    dates = [f"2020-{index // 28 + 1:02d}-{index % 28 + 1:02d}" for index in range(1000)]
    split = split_dates(dates)
    ordered = sorted(dates)
    index = {value: position for position, value in enumerate(ordered)}
    sections = ("train", "fit_validation", "calibration", "policy_validation", "test")
    for left, right in zip(sections, sections[1:]):
        distance = min(index[value] for value in split[right]) - max(
            index[value] for value in split[left]
        )
        assert distance >= 11
    assert split["test"].isdisjoint(split["train"])


def test_selection_is_date_local_and_has_fifteen_name_cap() -> None:
    rows = [
        {
            "symbol": f"S{index:02d}",
            "market_date": "2026-01-02",
        }
        for index in range(30)
    ]
    selected, diagnostics = select_rows(
        rows, np.arange(30, dtype=float), 0.40
    )
    assert len(selected) == 15
    assert {row["symbol"] for row in selected} == {
        f"S{index:02d}" for index in range(15, 30)
    }
    assert diagnostics["boundary_tie_abstentions"] == 0


def test_drawdown_scales_each_trade_to_one_of_seventy_five_slots() -> None:
    row = {
        "round_trip_cost_pct": 0.25,
        "label_5d_mark_to_market_path": [
            {
                "market_date": f"2026-01-0{index + 2}",
                "gross_return_from_entry_pct": value,
            }
            for index, value in enumerate((-1.0, -2.0, -3.0, -4.0, -5.0))
        ],
    }
    drawdown = mark_to_market_drawdown([row])
    assert drawdown is not None
    assert -0.071 < drawdown < -0.069


def test_policy_gate_requires_positive_typical_trade_and_rank_ic() -> None:
    base = {
        "count": 100,
        "distinct_market_dates": 20,
        "mean_net_return_pct": 0.5,
        "median_net_return_pct": -0.1,
        "win_rate": 0.55,
        "rank_ic": {"mean_spearman_rank_ic": 0.02},
        "top_minus_bottom_mean_net_pct": 0.4,
        "capital_scaled_max_drawdown_pct": -5.0,
    }
    passed, failures = policy_gate(base)
    assert not passed
    assert "positive_median" in failures
    base["median_net_return_pct"] = 0.1
    passed, failures = policy_gate(base)
    assert passed
    assert failures == []
