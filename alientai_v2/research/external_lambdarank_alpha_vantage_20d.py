from __future__ import annotations

"""Source-pure Alpha Vantage inputs for the isolated 20-session ranker."""

import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from alientai_v2.research.external_lambdarank_20d import (
    CONTEXT_SYMBOL,
    EMBARGO_SESSIONS,
    FEATURE_COLUMNS,
    HORIZON_SESSIONS,
    MINIMUM_CANDIDATES,
    PACKAGE_SHA256,
    RAW_FEATURES,
    ROUND_TRIP_COST_PCT,
    UNTRUSTED_JOBLIB_SHA256,
    build_panels,
    purged_folds,
    read_symbols,
    relevance_counts,
    score_metrics,
    select_latest,
    sha256,
)


MODEL_ID = "external_lambdarank_120_h20_alpha_vantage_v2_20260806"
SOURCE_ENDPOINT = "TIME_SERIES_DAILY_ADJUSTED"
SOURCE_OUTPUTSIZE = "full"
SEALED_TEST_FRACTION = 0.20


def _daily_path(archive: Path, symbol: str) -> Path:
    safe = symbol.replace("/", "-").replace(".", "-")
    return archive / f"{safe}_daily.json"


def _time_series(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    matches = [
        value
        for key, value in payload.items()
        if str(key).startswith("Time Series") and isinstance(value, dict)
    ]
    if len(matches) != 1 or not matches[0]:
        raise ValueError("expected one nonempty Alpha Vantage daily series")
    return matches[0]


def _valid_adjusted_values(values: dict[str, Any]) -> bool:
    numeric = [
        float(values[name])
        for name in ("open", "high", "low", "close", "volume")
    ]
    price_scale = max(
        float(values[name]) for name in ("open", "high", "low", "close")
    )
    tolerance = max(1e-12, price_scale * 1e-12)
    return (
        all(np.isfinite(value) for value in numeric)
        and min(
            float(values[name])
            for name in ("open", "high", "low", "close")
        )
        > 0.0
        and float(values["volume"]) >= 0.0
        and float(values["high"]) + tolerance
        >= max(
            float(values["open"]),
            float(values["low"]),
            float(values["close"]),
        )
        and float(values["low"]) - tolerance
        <= min(
            float(values["open"]),
            float(values["high"]),
            float(values["close"]),
        )
    )


def _point_in_time_volume(row: dict[str, Any]) -> float:
    """Return only volume observable on the row's own market date."""
    return float(row["6. volume"])


def load_alpha_vantage_daily_archive(
    archive: Path,
    symbols: Sequence[str],
    *,
    as_of_session: str | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    expected = [*symbols, CONTEXT_SYMBOL]
    if (
        len(symbols) != MINIMUM_CANDIDATES
        or len(expected) != len(set(expected))
        or CONTEXT_SYMBOL in symbols
    ):
        raise ValueError("exact 120-candidate plus SPY universe is required")
    audit_path = archive / "content_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if (
        audit.get("status") != "PASS"
        or audit.get("provider") != "Alpha Vantage"
        or audit.get("endpoint") != SOURCE_ENDPOINT
        or audit.get("outputsize") not in {"compact", "full"}
        or int(audit.get("expected_symbols") or 0) != len(expected)
        or int(audit.get("audited_symbols") or 0) != len(expected)
        or audit.get("failures")
        or audit.get("orphan_files")
    ):
        raise ValueError("Alpha Vantage archive content audit is not usable")

    daily: dict[str, list[dict[str, Any]]] = {}
    files: dict[str, dict[str, Any]] = {}
    for symbol in expected:
        path = _daily_path(archive, symbol)
        details = audit["files"].get(symbol)
        if not details or sha256(path) != details.get("sha256"):
            raise ValueError(f"{symbol} source hash mismatch")
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload_symbol = str(
            (payload.get("Meta Data") or {}).get("2. Symbol") or ""
        ).upper()
        if payload_symbol != symbol:
            raise ValueError(f"{symbol} payload identity mismatch")
        source = _time_series(payload)
        ordered_dates = sorted(
            market_date
            for market_date in source
            if as_of_session is None or market_date <= as_of_session
        )
        rows = []
        for market_date in ordered_dates:
            row = source[market_date]
            split = float(row["8. split coefficient"])
            if not np.isfinite(split) or split <= 0.0:
                raise ValueError(f"{symbol} invalid split coefficient")
            raw_close = float(row["4. close"])
            adjusted_close = float(row["5. adjusted close"])
            factor = adjusted_close / raw_close
            values = {
                "symbol": symbol,
                "market_date": market_date,
                "open": float(row["1. open"]) * factor,
                "high": float(row["2. high"]) * factor,
                "low": float(row["3. low"]) * factor,
                "close": adjusted_close,
                # Use only volume observable on this market date. Applying a
                # cumulative future split factor here would leak a later
                # corporate action into relative-volume features.
                "volume": _point_in_time_volume(row),
            }
            if not _valid_adjusted_values(values):
                raise ValueError(f"{symbol} invalid adjusted row {market_date}")
            rows.append(values)
        if len(rows) < 100:
            raise ValueError(f"{symbol} has insufficient adjusted history")
        daily[symbol] = rows
        files[symbol] = {
            "path": str(path.resolve()),
            "sha256": details["sha256"],
            "rows": len(rows),
            "first_market_date": rows[0]["market_date"],
            "last_market_date": rows[-1]["market_date"],
        }
    return daily, {
        "provider": "Alpha Vantage",
        "endpoint": SOURCE_ENDPOINT,
        "outputsize": audit["outputsize"],
        "archive": str(archive.resolve()),
        "content_audit_path": str(audit_path.resolve()),
        "content_audit_sha256": sha256(audit_path),
        "as_of_session": as_of_session,
        "price_adjustment": (
            "OHLC multiplied by same-date adjusted_close/raw_close"
        ),
        "volume_adjustment": (
            "raw point-in-time volume; no future split adjustment"
        ),
        "files": files,
    }


def chronological_panel_split(
    frame: pd.DataFrame,
    *,
    sealed_fraction: float = SEALED_TEST_FRACTION,
    boundary_embargo_sessions: int = EMBARGO_SESSIONS,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    dates = sorted(frame["market_date"].astype(str).unique())
    if len(dates) < 200 or not 0.10 <= sealed_fraction <= 0.40:
        raise ValueError("insufficient dates or invalid sealed fraction")
    sealed_index = int(np.floor(len(dates) * (1.0 - sealed_fraction)))
    sealed_index = max(1, min(sealed_index, len(dates) - 1))
    sealed_dates = dates[sealed_index:]
    presealed_dates = dates[:sealed_index]
    if len(presealed_dates) <= boundary_embargo_sessions:
        raise ValueError("insufficient presealed dates for boundary embargo")
    embargo_dates = presealed_dates[-boundary_embargo_sessions:]
    eligible_development = set(
        presealed_dates[:-boundary_embargo_sessions]
    )
    sealed_start = sealed_dates[0]
    development = frame[
        frame["market_date"].astype(str).isin(eligible_development)
        & (frame["label_exit_date"].astype(str) < sealed_start)
    ].copy().reset_index(drop=True)
    sealed = frame[
        frame["market_date"].astype(str).isin(set(sealed_dates))
    ].copy().reset_index(drop=True)
    if development.empty or sealed.empty:
        raise ValueError("chronological split produced an empty partition")
    overlap = set(development["market_date"].astype(str)) & set(
        sealed["market_date"].astype(str)
    )
    if overlap:
        raise ValueError("development and sealed dates overlap")
    if development["label_exit_date"].astype(str).max() >= sealed_start:
        raise ValueError("development labels overlap sealed test")
    return development, sealed, {
        "sealed_fraction_requested": sealed_fraction,
        "sealed_start_date": sealed_start,
        "development_first_date": str(
            development["market_date"].astype(str).min()
        ),
        "development_last_date": str(
            development["market_date"].astype(str).max()
        ),
        "development_dates": int(development["market_date"].nunique()),
        "development_rows": len(development),
        "boundary_embargo_dates": embargo_dates,
        "boundary_embargo_sessions": boundary_embargo_sessions,
        "sealed_first_date": str(sealed["market_date"].astype(str).min()),
        "sealed_last_date": str(sealed["market_date"].astype(str).max()),
        "sealed_dates": int(sealed["market_date"].nunique()),
        "sealed_rows": len(sealed),
    }


__all__ = [
    "CONTEXT_SYMBOL",
    "EMBARGO_SESSIONS",
    "FEATURE_COLUMNS",
    "HORIZON_SESSIONS",
    "MINIMUM_CANDIDATES",
    "MODEL_ID",
    "PACKAGE_SHA256",
    "RAW_FEATURES",
    "ROUND_TRIP_COST_PCT",
    "SOURCE_ENDPOINT",
    "SOURCE_OUTPUTSIZE",
    "SEALED_TEST_FRACTION",
    "UNTRUSTED_JOBLIB_SHA256",
    "build_panels",
    "chronological_panel_split",
    "load_alpha_vantage_daily_archive",
    "purged_folds",
    "read_symbols",
    "relevance_counts",
    "score_metrics",
    "select_latest",
    "sha256",
]
