"""Leakage-safe natural-universe premarket feature join for the challenger."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any, Iterable, Mapping


MAXIMUM_PREMARKET_CUTOFF = time(9, 25)


def _key(row: Mapping[str, Any]) -> tuple[str, str]:
    symbol = str(row.get("symbol") or "").upper().strip()
    market_date = str(row.get("market_date") or "").strip()
    if not symbol or not market_date:
        raise ValueError("every premarket row requires symbol and market_date")
    return symbol, market_date


def _unique(rows: Iterable[Mapping[str, Any]], name: str) -> dict[tuple[str, str], Mapping[str, Any]]:
    result = {}
    for row in rows:
        key = _key(row)
        if key in result:
            raise ValueError(f"duplicate {name} key: {key[0]} {key[1]}")
        result[key] = row
    return result


def join_natural_premarket_features(
    base_rows: Iterable[Mapping[str, Any]],
    premarket_rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Require an exact natural-universe panel and enforce the 09:25 ET cutoff."""
    base = _unique(base_rows, "base")
    premarket = _unique(premarket_rows, "premarket")
    if set(base) != set(premarket):
        raise ValueError(
            "natural premarket keys must match the base panel exactly; "
            f"missing={len(set(base) - set(premarket))} extra={len(set(premarket) - set(base))}"
        )

    joined = []
    for key in sorted(base, key=lambda item: (item[1], item[0])):
        feature = premarket[key]
        biased = sorted(name for name in feature if name.startswith("study_"))
        if biased:
            raise ValueError(
                "matched winner/control metadata is forbidden in natural premarket input: "
                + ", ".join(biased)
            )
        if feature.get("premarket_available") is True:
            cutoff = str(feature.get("premarket_cutoff_et") or "")
            if cutoff != "09:25":
                raise ValueError(f"premarket cutoff must be 09:25 ET for {key[0]} {key[1]}")
            timestamp = datetime.fromisoformat(str(feature.get("premarket_last_timestamp_et") or ""))
            if timestamp.date().isoformat() != key[1] or timestamp.time() > MAXIMUM_PREMARKET_CUTOFF:
                raise ValueError(f"premarket timestamp exceeds decision cutoff for {key[0]} {key[1]}")

        fields = {
            name: value for name, value in feature.items()
            if name.startswith("premarket_")
        }
        joined.append({**base[key], **fields})
    return joined
