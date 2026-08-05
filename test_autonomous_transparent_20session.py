from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from evaluate_autonomous_transparent_20session_outcomes import (
    append_unique,
    build_outcomes,
    summarize,
)


def write_daily(path, count: int) -> None:
    start = date(2026, 1, 1)
    rows = []
    for index in range(count):
        close = 100.0 + index
        rows.append(
            {
                "date": str(start + timedelta(days=index)),
                "1. open": str(close - 0.5),
                "2. high": str(close + 1.0),
                "3. low": str(close - 1.0),
                "4. close": str(close),
                "5. adjusted close": str(close),
                "6. volume": "1000000",
                "8. split coefficient": "1.0",
            }
        )
    path.write_text(
        json.dumps(
            {
                "Meta Data": {},
                "Time Series (Daily)": {
                    row.pop("date"): row for row in reversed(rows)
                },
            }
        ),
        encoding="utf-8",
    )


def journal(decision_date: str) -> dict:
    return {
        "model_family": (
            "transparent cross-sectional 126/60-session momentum "
            "plus inverse 60-session volatility"
        ),
        "decision_date": decision_date,
        "frozen_report_sha256": "abc123",
        "round_trip_cost_pct": 0.25,
        "selections": [{"rank": 1, "symbol": "AAA"}],
    }


def test_outcome_uses_next_open_and_twentieth_subsequent_close(
    tmp_path,
) -> None:
    write_daily(tmp_path / "AAA_daily.json", 30)
    decision = str(date(2026, 1, 1) + timedelta(days=2))
    complete, pending = build_outcomes(
        journal_rows=[journal(decision)],
        daily_root=tmp_path,
    )
    assert pending == []
    assert len(complete) == 1
    row = complete[0]
    assert row["entry_market_date"] == str(
        date(2026, 1, 1) + timedelta(days=3)
    )
    assert row["exit_market_date"] == str(
        date(2026, 1, 1) + timedelta(days=22)
    )
    expected = (122.0 / 102.5 - 1.0) * 100.0
    assert row["gross_return_pct"] == pytest.approx(expected)
    assert row["net_return_pct"] == pytest.approx(expected - 0.25)


def test_incomplete_horizon_stays_pending(tmp_path) -> None:
    write_daily(tmp_path / "AAA_daily.json", 10)
    decision = str(date(2026, 1, 1) + timedelta(days=2))
    complete, pending = build_outcomes(
        journal_rows=[journal(decision)],
        daily_root=tmp_path,
    )
    assert complete == []
    assert pending[0]["status"] == "PENDING_HORIZON"
    assert pending[0]["available_future_sessions"] == 7


def test_append_is_identity_idempotent_and_summary_is_post_cost(
    tmp_path,
) -> None:
    path = tmp_path / "outcomes.jsonl"
    rows = [
        {
            "status": "COMPLETE",
            "frozen_report_sha256": "hash",
            "decision_date": "2026-01-01",
            "symbol": "AAA",
            "net_return_pct": 1.0,
        }
    ]
    assert append_unique(path, rows) == 1
    assert append_unique(path, rows) == 0
    result = summarize(rows)
    assert result["signals"] == 1
    assert result["mean_net_return_pct"] == 1.0
    assert result["win_rate_after_cost_pct"] == 100.0
