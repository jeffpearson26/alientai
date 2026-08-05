from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from build_nasdaq_qqq_spy_60session_panel import (
    build_rows,
    load_adjusted_daily,
    read_overlay,
)
from train_nasdaq_qqq_spy_60session_clone import (
    capital_scaled_drawdown,
    newey_west_standard_error,
    select_daily,
    select_daily_with_diagnostics,
    split_dates,
)


def candles(count: int = 125, offset: float = 0.0) -> list[dict]:
    start = date(2020, 1, 1)
    return [
        {
            "market_date": str(start + timedelta(days=index)),
            "open": 100.0 + offset + index,
            "high": 101.0 + offset + index,
            "low": 99.0 + offset + index,
            "close": 100.5 + offset + index,
            "volume": 1_000_000.0 + index,
            "adjustment_factor": 1.0,
        }
        for index in range(count)
    ]


def test_adjusted_daily_applies_price_factor(tmp_path: Path) -> None:
    path = tmp_path / "AAA_daily.json"
    path.write_text(json.dumps({
        "Time Series (Daily)": {
            "2020-01-02": {
                "1. open": "100",
                "2. high": "110",
                "3. low": "90",
                "4. close": "100",
                "5. adjusted close": "25",
                "6. volume": "1000",
            }
        }
    }), encoding="utf-8")
    row = load_adjusted_daily(path)[0]
    assert row["open"] == 25.0
    assert row["high"] == 27.5
    assert row["low"] == 22.5
    assert row["close"] == 25.0
    assert row["volume"] == 4000.0


def test_sixty_session_label_uses_next_open_and_sixtieth_close() -> None:
    daily = {
        "AAA": candles(offset=2.0),
        "QQQ": candles(offset=1.0),
        "SPY": candles(offset=0.0),
    }
    rows = build_rows(daily, ["AAA", "QQQ", "SPY"], {}, "2020-01-01")
    first = next(
        row for row in rows
        if row["symbol"] == "AAA" and row["return_60d_lag_pct"] is not None
    )
    source = daily["AAA"]
    decision = 60
    assert first["market_date"] == source[decision]["market_date"]
    assert first["label_entry_market_date"] == source[decision + 1]["market_date"]
    assert first["label_60d_exit_market_date"] == source[decision + 60]["market_date"]
    expected = (
        source[decision + 60]["close"] / source[decision + 1]["open"] - 1.0
    ) * 100.0
    assert first["label_60d_gross_return_pct"] == round(expected, 6)
    assert first["label_60d_net_return_pct"] == round(expected - 0.25, 6)
    assert first["relative_to_qqq_60d_pct"] == pytest.approx(
        first["return_60d_lag_pct"] - first["qqq_return_60d_pct"]
    )


def test_overlay_excludes_all_labels(tmp_path: Path) -> None:
    path = tmp_path / "overlay.jsonl"
    path.write_text(json.dumps({
        "symbol": "AAA",
        "market_date": "2020-01-01",
        "model_news_article_count": 2,
        "model_call_volume_unusual": True,
        "label_forward_return_5d_pct": 50.0,
    }) + "\n", encoding="utf-8")
    overlay, _ = read_overlay(path)
    row = overlay[("AAA", "2020-01-01")]
    assert row["model_news_article_count"] == 2
    assert row["model_call_volume_unusual"] is True
    assert not any(name.startswith("label_") for name in row)


def test_split_has_sixty_session_two_sided_gaps() -> None:
    start = date(2020, 1, 1)
    dates = [str(start + timedelta(days=index)) for index in range(1800)]
    split = split_dates(dates)
    ordered = sorted(dates)
    names = ("train", "fit_validation", "calibration", "policy_validation", "test")
    for left, right in zip(names, names[1:]):
        gap = (
            ordered.index(min(split[right]))
            - ordered.index(max(split[left]))
            - 1
        )
        assert gap >= 60


def test_selection_can_pick_qqq_and_spy_but_may_abstain() -> None:
    rows = [
        {"market_date": "2020-01-02", "symbol": symbol}
        for symbol in ("AAA", "QQQ", "SPY")
    ]
    assert select_daily(rows, np.zeros(3), 1.0) == []
    selected = select_daily(rows, np.asarray([0.1, 0.8, 0.9]), 0.5)
    assert {row["symbol"] for row in selected} == {"QQQ", "SPY"}


def test_selection_abstains_when_fifth_place_is_tied() -> None:
    rows = [
        {"market_date": "2020-01-02", "symbol": f"S{index:02d}"}
        for index in range(10)
    ]
    selected, diagnostics = select_daily_with_diagnostics(
        rows, np.ones(10), 0.5
    )
    assert selected == []
    assert diagnostics["boundary_tie_abstentions"] == 1


def test_hac_and_capital_scaling_are_not_full_notional() -> None:
    values = np.linspace(-1.0, 1.0, 100)
    assert newey_west_standard_error(values, 59) is not None
    rows = [
        {
            "label_60d_exit_market_date": "2020-06-01",
            "label_60d_net_return_pct": -10.0,
        }
        for _ in range(5)
    ]
    assert capital_scaled_drawdown(rows) == pytest.approx(-1.0 / 6.0)
