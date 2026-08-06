from __future__ import annotations

import json
from pathlib import Path

import pytest

from alientai_v2.research.nasdaq_ai_roadmap_5d import (
    read_symbols,
    validate_contract,
    validate_membership_rows,
    validate_point_in_time_rows,
)


def test_contract_preserves_exact_horizon_cost_and_safety() -> None:
    contract = json.loads(
        Path("nasdaq_ai_roadmap_5d_contract.json").read_text(
            encoding="utf-8"
        )
    )
    validate_contract(contract)
    assert contract["timing"]["horizon_sessions"] == 5
    assert contract["timing"]["round_trip_cost_pct"] == 0.25
    assert contract["execution_enabled"] is False


def test_exact_overlay_has_22_unique_symbols_and_expected_union() -> None:
    nasdaq = read_symbols(Path("nasdaq100_2026-06_symbols.txt"))
    overlay = read_symbols(
        Path("research_universes/nasdaq_ai_roadmap_overlay_20260805.txt")
    )
    assert len(nasdaq) == 101
    assert len(overlay) == 22
    assert len(set(nasdaq) | set(overlay)) == 103
    assert set(overlay) - set(nasdaq) == {"ON", "TSM"}


def test_membership_requires_provenance_and_known_time() -> None:
    errors = validate_membership_rows(
        [
            {
                "effective_from": "2025-01-01",
                "symbols": [f"S{index:03d}" for index in range(100)],
            }
        ]
    )
    assert any("source provenance" in error for error in errors)
    assert any("known_at_utc" in error for error in errors)


def test_point_in_time_rows_reject_future_fields() -> None:
    errors = validate_point_in_time_rows(
        [
            {
                "symbol": "NVDA",
                "available_at_utc": "2026-08-01T20:00:00+00:00",
                "revenue_growth_yoy": 1.0,
                "label_future_return": 9.0,
            }
        ],
        {"symbol", "available_at_utc", "revenue_growth_yoy"},
    )
    assert any("forbidden" in error for error in errors)


def test_contract_rejects_random_shuffle() -> None:
    contract = json.loads(
        Path("nasdaq_ai_roadmap_5d_contract.json").read_text(
            encoding="utf-8"
        )
    )
    contract["validation"]["random_shuffle"] = True
    with pytest.raises(ValueError, match="shuffling"):
        validate_contract(contract)
