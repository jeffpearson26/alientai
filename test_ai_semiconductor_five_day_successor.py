from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from build_ai_semiconductor_five_day_successor_panel import (
    build_rows,
    read_overlay,
)
from train_ai_semiconductor_five_day_successor import (
    capital_scaled_drawdown,
    ensemble_score,
    fit_ensemble_standardization,
    select_daily,
    split_dates,
)


def candles(count: int = 70) -> list[dict]:
    return [
        {
            "market_date": f"2025-01-{index + 1:02d}",
            "open": 100.0 + index,
            "high": 101.0 + index,
            "low": 99.0 + index,
            "close": 100.5 + index,
            "volume": 1_000_000 + index,
        }
        for index in range(count)
    ]


def test_panel_uses_next_open_and_fifth_close() -> None:
    source = candles()
    rows = list(build_rows({"AAA": source}, {}))
    first = rows[0]
    decision_index = 59
    assert first["market_date"] == source[decision_index]["market_date"]
    assert first["label_entry_market_date"] == source[decision_index + 1]["market_date"]
    assert first["label_entry_next_open"] == source[decision_index + 1]["open"]
    assert first["label_5d_exit_market_date"] == source[decision_index + 5]["market_date"]
    expected = (
        source[decision_index + 5]["close"]
        / source[decision_index + 1]["open"]
        - 1.0
    ) * 100.0
    assert first["label_5d_gross_return_pct"] == round(expected, 6)
    assert first["label_5d_net_return_pct"] == round(expected - 0.25, 6)


def test_overlay_cannot_copy_future_labels(tmp_path: Path) -> None:
    path = tmp_path / "overlay.jsonl"
    path.write_text(json.dumps({
        "symbol": "AAA",
        "market_date": "2025-01-01",
        "narrative_news_available": True,
        "model_call_volume_unusual": True,
        "label_5d_net_return_pct": 99.0,
    }) + "\n", encoding="utf-8")
    overlay, _ = read_overlay(path)
    row = overlay[("AAA", "2025-01-01")]
    assert row["narrative_news_available"] is True
    assert row["model_call_volume_unusual"] is True
    assert "label_5d_net_return_pct" not in row


def test_date_splits_have_two_sided_embargoes() -> None:
    dates = [f"2025-{1 + index // 28:02d}-{1 + index % 28:02d}" for index in range(280)]
    split = split_dates(dates)
    assigned = set().union(*split.values())
    assert assigned == set(dates)
    names = ("train", "fit_validation", "calibration", "policy_validation", "test")
    for left, right in zip(names, names[1:]):
        assert max(split[left]) < min(split[right])
        all_dates = sorted(dates)
        gap = all_dates.index(min(split[right])) - all_dates.index(max(split[left])) - 1
        assert gap >= 5


def test_daily_selection_allows_abstention_and_caps_at_five() -> None:
    rows = [
        {"market_date": "2025-01-02", "symbol": f"S{index:02d}"}
        for index in range(10)
    ]
    assert select_daily(rows, np.zeros(10), 0.5) == []
    selected = select_daily(rows, np.arange(10, dtype=float), 2.0)
    assert len(selected) == 5
    assert {row["symbol"] for row in selected} == {
        "S05", "S06", "S07", "S08", "S09"
    }


def test_daily_selection_respects_predeclared_eligibility() -> None:
    rows = [
        {
            "market_date": "2025-01-02",
            "symbol": f"S{index:02d}",
            "eligible": index % 2 == 0,
        }
        for index in range(10)
    ]
    selected = select_daily(
        rows, np.arange(10, dtype=float), 0.0, eligibility_field="eligible"
    )
    assert [row["symbol"] for row in selected] == [
        "S08", "S06", "S04", "S02", "S00"
    ]


def test_drawdown_is_cash_scaled_for_25_overlapping_slots() -> None:
    rows = [
        {
            "label_5d_exit_market_date": "2025-01-10",
            "label_5d_net_return_pct": -10.0,
        }
        for _ in range(5)
    ]
    assert capital_scaled_drawdown(rows) == pytest.approx(-2.0)


def test_fixed_ensemble_preserves_ranking_information() -> None:
    classifier = np.asarray([0.40, 0.50, 0.60])
    returns = np.asarray([-1.0, 0.0, 1.0])
    values = fit_ensemble_standardization(classifier, returns)
    combined = ensemble_score(classifier, returns, values)
    assert combined[0] < combined[1] < combined[2]
