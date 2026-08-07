from __future__ import annotations

"""Point-in-time universe screen for the frozen Nasdaq baseline clone."""

import csv
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


MODEL_ID = "us_smallcap_range_volume_baseline_clone_h05_v1_20260807"
NASDAQ_MODEL_ID = "nasdaq_smallcap_range_volume_baseline_clone_h05_v1_20260807"
SOURCE_MODEL_ID = "nasdaq100_complete_101_baseline_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp is not timezone-aware: {value}")
    return parsed.astimezone(timezone.utc)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def active_stock_symbols(
    path: Path,
    *,
    allowed_exchanges: Sequence[str] | None = None,
) -> list[str]:
    opener = gzip.open if path.suffix.casefold() == ".gz" else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "symbol",
        "exchange",
        "assetType",
        "status",
    }
    if not rows or not required.issubset(rows[0]):
        raise ValueError("listing file is empty or missing required columns")
    allowed = (
        {value.strip().upper() for value in allowed_exchanges}
        if allowed_exchanges
        else None
    )
    output: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if str(row.get("status") or "").strip().casefold() != "active":
            continue
        if str(row.get("assetType") or "").strip().casefold() != "stock":
            continue
        exchange = str(row.get("exchange") or "").strip().upper()
        if allowed is not None and exchange not in allowed:
            continue
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            raise ValueError("active stock listing has a blank symbol")
        if symbol in seen:
            raise ValueError(f"duplicate active stock listing: {symbol}")
        seen.add(symbol)
        output.append(symbol)
    if not output:
        raise ValueError("listing contains no active stocks")
    return sorted(output)


def unique_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    expected_provider: str,
    timestamp_field: str,
    cutoff_utc: datetime,
) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for source in rows:
        row = dict(source)
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            raise ValueError("snapshot row has a blank symbol")
        if symbol in output:
            raise ValueError(f"duplicate snapshot symbol: {symbol}")
        provider = str(row.get("provider") or "").strip().casefold()
        if provider != expected_provider.casefold():
            raise ValueError(
                f"{symbol} provider {provider!r} does not match "
                f"{expected_provider!r}"
            )
        available = parse_utc(str(row.get(timestamp_field) or ""))
        if available > cutoff_utc:
            raise ValueError(
                f"{symbol} {timestamp_field} is after the decision cutoff"
            )
        output[symbol] = row
    return output


def _number(row: Mapping[str, Any], name: str) -> float:
    value = row.get(name)
    if value is None or value == "":
        raise ValueError(f"missing required value {name}")
    parsed = float(value)
    if parsed != parsed:
        raise ValueError(f"non-finite required value {name}")
    return parsed


def screen_universe(
    listing_symbols: Sequence[str],
    technical_rows: Sequence[Mapping[str, Any]],
    market_cap_rows: Sequence[Mapping[str, Any]],
    *,
    decision_date: str,
    cutoff_utc: datetime,
    provider: str,
    maximum_market_cap_usd: float,
    maximum_price_usd: float,
    minimum_relative_volume_20: float,
    minimum_atr14_pct: float,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    technical = unique_rows(
        technical_rows,
        expected_provider=provider,
        timestamp_field="available_at_utc",
        cutoff_utc=cutoff_utc,
    )
    market_caps = unique_rows(
        market_cap_rows,
        expected_provider=provider,
        timestamp_field="available_at_utc",
        cutoff_utc=cutoff_utc,
    )
    listing = set(listing_symbols)
    counts = {
        "active_stocks": len(listing),
        "missing_technical": 0,
        "missing_market_cap": 0,
        "wrong_decision_date": 0,
        "market_cap_rejected": 0,
        "price_rejected": 0,
        "relative_volume_rejected": 0,
        "uptrend_rejected": 0,
        "range_rejected": 0,
        "eligible": 0,
    }
    eligible: list[dict[str, Any]] = []
    for symbol in sorted(listing):
        technical_row = technical.get(symbol)
        market_cap_row = market_caps.get(symbol)
        if technical_row is None:
            counts["missing_technical"] += 1
            continue
        if market_cap_row is None:
            counts["missing_market_cap"] += 1
            continue
        if str(technical_row.get("market_date") or "") != decision_date:
            counts["wrong_decision_date"] += 1
            continue
        market_cap = _number(market_cap_row, "market_cap_usd")
        close = _number(technical_row, "close")
        relative_volume = _number(
            technical_row,
            "technical_latest_relative_volume_20",
        )
        atr14_pct = _number(technical_row, "technical_atr14_pct")
        if not 0.0 < market_cap < maximum_market_cap_usd:
            counts["market_cap_rejected"] += 1
            continue
        if not 0.0 < close < maximum_price_usd:
            counts["price_rejected"] += 1
            continue
        if relative_volume < minimum_relative_volume_20:
            counts["relative_volume_rejected"] += 1
            continue
        uptrend = (
            technical_row.get("technical_ema_bullish_alignment") is True
            and _number(technical_row, "technical_ema9_distance_pct") > 0.0
            and _number(technical_row, "technical_ema21_distance_pct") > 0.0
            and _number(technical_row, "technical_ema50_distance_pct") > 0.0
        )
        if not uptrend:
            counts["uptrend_rejected"] += 1
            continue
        if atr14_pct < minimum_atr14_pct:
            counts["range_rejected"] += 1
            continue
        eligible.append(
            {
                **technical_row,
                "symbol": symbol,
                "market_cap_usd": market_cap,
                "screen_close_usd": close,
                "screen_relative_volume_20": relative_volume,
                "screen_atr14_pct": atr14_pct,
                "screen_uptrend": True,
            }
        )
    counts["eligible"] = len(eligible)
    return eligible, counts


def validate_clone_contract(
    contract: Mapping[str, Any],
    *,
    model_path: Path,
    report_path: Path,
) -> None:
    if contract.get("model_id") not in {MODEL_ID, NASDAQ_MODEL_ID}:
        raise ValueError("clone model ID mismatch")
    if contract.get("source_model_id") != SOURCE_MODEL_ID:
        raise ValueError("source model ID mismatch")
    if int(contract.get("horizon_sessions") or 0) != 5:
        raise ValueError("clone horizon changed")
    if float(contract.get("round_trip_cost_pct") or -1) != 0.25:
        raise ValueError("clone cost changed")
    artifacts = contract.get("source_artifacts") or {}
    if sha256(model_path) != artifacts.get("model_sha256"):
        raise ValueError("source model hash mismatch")
    if sha256(report_path) != artifacts.get("report_sha256"):
        raise ValueError("source report hash mismatch")


def score_candidates(
    rows: Sequence[Mapping[str, Any]],
    *,
    model: Any,
    feature_names: Sequence[str],
    score_cutoff: float,
    maximum_selections: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    import numpy as np

    if not rows:
        return [], []
    matrix = np.asarray(
        [
            [_number(row, name) for name in feature_names]
            for row in rows
        ],
        dtype=np.float32,
    )
    scores = model.predict(matrix, num_iteration=model.best_iteration)
    scored = sorted(
        [
            {**dict(row), "technical_context_score": float(score)}
            for row, score in zip(rows, scores)
        ],
        key=lambda row: (-row["technical_context_score"], row["symbol"]),
    )
    selected = [
        row
        for row in scored
        if row["technical_context_score"] >= score_cutoff
    ][:maximum_selections]
    return scored, selected
