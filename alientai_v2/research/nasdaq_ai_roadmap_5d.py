from __future__ import annotations

"""Contracts and readiness helpers for the exact Nasdaq/AI five-day roadmap."""

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


REQUIRED_CONTEXT_SYMBOLS = ("QQQ", "SMH", "SOXX", "VIX", "NVDA")
REQUIRED_POINT_IN_TIME_COLUMNS = {
    "fundamentals": {
        "symbol",
        "available_at_utc",
        "revenue_growth_yoy",
        "eps_growth_yoy",
        "gross_margin",
        "gross_margin_change",
        "earnings_beat_miss_streak",
    },
    "earnings_calendar": {
        "symbol",
        "event_at_utc",
        "available_at_utc",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_symbols(path: Path) -> list[str]:
    symbols = [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not symbols:
        raise ValueError(f"empty symbol file: {path}")
    if len(symbols) != len(set(symbols)):
        raise ValueError(f"duplicate symbols in {path}")
    return symbols


def load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def validate_contract(contract: Mapping[str, Any]) -> None:
    if contract.get("schema_version") != 1:
        raise ValueError("unsupported roadmap contract schema")
    if contract.get("model_id") != "nasdaq_ai_roadmap_cross_sectional_5d_v1":
        raise ValueError("unexpected model id")
    timing = contract.get("timing") or {}
    if timing.get("horizon_sessions") != 5:
        raise ValueError("roadmap horizon must remain five sessions")
    if timing.get("round_trip_cost_pct") != 0.25:
        raise ValueError("roadmap cost must remain 0.25%")
    validation = contract.get("validation") or {}
    if validation.get("random_shuffle") is not False:
        raise ValueError("random time shuffling is prohibited")
    if validation.get("embargo_sessions_each_side") != 5:
        raise ValueError("five-session embargo contract changed")
    if contract.get("execution_enabled") is not False:
        raise ValueError("research model cannot enable execution")


def validate_membership_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Validate quarterly point-in-time membership without inferring membership."""
    errors: list[str] = []
    prior_effective = ""
    for index, row in enumerate(rows, start=1):
        effective = str(row.get("effective_from") or "")
        symbols = row.get("symbols")
        if not effective:
            errors.append(f"membership row {index} lacks effective_from")
        if prior_effective and effective <= prior_effective:
            errors.append("membership effective_from values are not increasing")
        prior_effective = effective
        if not isinstance(symbols, list) or not symbols:
            errors.append(f"membership row {index} lacks symbols")
            continue
        normalized = [str(symbol).upper() for symbol in symbols]
        if len(normalized) != len(set(normalized)):
            errors.append(f"membership row {index} contains duplicates")
        if not 95 <= len(normalized) <= 105:
            errors.append(
                f"membership row {index} has implausible count {len(normalized)}"
            )
        if row.get("source") in (None, ""):
            errors.append(f"membership row {index} lacks source provenance")
        if row.get("known_at_utc") in (None, ""):
            errors.append(f"membership row {index} lacks known_at_utc")
    if not rows:
        errors.append("membership history is empty")
    return errors


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"non-object at {path}:{line_number}")
            rows.append(value)
    return rows


def validate_point_in_time_rows(
    rows: Sequence[Mapping[str, Any]], required: Iterable[str]
) -> list[str]:
    required_set = set(required)
    errors = []
    for index, row in enumerate(rows, start=1):
        missing = sorted(required_set - set(row))
        if missing:
            errors.append(f"row {index} missing {missing}")
        available = str(row.get("available_at_utc") or "")
        if not available.endswith(("+00:00", "Z")):
            errors.append(f"row {index} available_at_utc is not explicit UTC")
        if any(
            name.startswith(("label_", "future_"))
            for name in row
        ):
            errors.append(f"row {index} contains forbidden future/label field")
    if not rows:
        errors.append("point-in-time table is empty")
    return errors


def manifest_symbols(root: Path) -> tuple[set[str], list[str]]:
    path = root / "manifest.json"
    if not path.exists():
        return set(), [f"missing manifest: {path}"]
    manifest = load_json(path)
    errors = []
    if manifest.get("status") != "complete":
        errors.append(f"manifest not complete: {path}")
    if manifest.get("failed"):
        errors.append(f"manifest has failures: {path}")
    if manifest.get("function") not in (None, "TIME_SERIES_DAILY_ADJUSTED"):
        errors.append(f"manifest is not adjusted daily: {path}")
    if manifest.get("outputsize") not in (None, "full"):
        errors.append(f"manifest is not full history: {path}")
    return {
        str(symbol).upper() for symbol in manifest.get("completed") or []
    }, errors
