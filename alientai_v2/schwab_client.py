"""Backward-compatible quote import.

New AlienTAI runtime work uses Alpha Vantage.  This module remains only so
older internal imports fail safely forward instead of dynamically loading an
ignored legacy source file.
"""
from __future__ import annotations

from typing import Any

from alientai_v2.alpha_vantage_quote_client import get_real_v2_quotes
from alientai_v2.utils import safe_float


def quote_value(raw: dict[str, Any], *names: str, default: float = 0.0) -> float:
    for name in names:
        if raw.get(name) is not None:
            return safe_float(raw.get(name), default)
    return default


def fetch_quotes_chunked(symbols: list[str], chunk_size: int = 100) -> dict[str, Any]:
    """Compatibility adapter around Alpha Vantage's native bulk quote client."""
    del chunk_size
    rows = get_real_v2_quotes(symbols)
    return {
        "status": "success" if len(rows) == len(set(symbols)) else "partial_success",
        "quotes": {row["symbol"]: row for row in rows},
        "source": "alpha_vantage_realtime_bulk_quote",
    }
