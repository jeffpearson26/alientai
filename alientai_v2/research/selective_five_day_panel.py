"""Exact-key, leakage-blocking panel join for selective five-day research."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping, Sequence


FORBIDDEN_FEATURE_FIELDS = {
    "entry_date",
    "entry_price",
    "exit_date",
    "exit_price",
    "future_market_date",
    "future_return_pct",
    "gross_return_pct",
    "net_return_pct",
    "realized_return_pct",
}


def _key(row: Mapping[str, Any], date_field: str) -> tuple[str, str]:
    symbol = str(row.get("symbol") or "").upper().strip()
    day = str(row.get(date_field) or "").strip()
    if not symbol or not day:
        raise ValueError(f"every row requires symbol and {date_field}")
    try:
        date.fromisoformat(day)
    except ValueError as exc:
        raise ValueError(f"invalid {date_field}: {day}") from exc
    return symbol, day


def _index_unique(
    rows: Iterable[Mapping[str, Any]],
    date_field: str,
    name: str,
) -> dict[tuple[str, str], Mapping[str, Any]]:
    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in rows:
        key = _key(row, date_field)
        if key in result:
            raise ValueError(f"duplicate {name} key: {key[0]} {key[1]}")
        result[key] = row
    return result


def _utc_moment(value: Any, field_name: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"feature row requires {field_name}")
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid {field_name}: {text}") from exc
    if moment.tzinfo is None:
        raise ValueError(f"{field_name} must include a timezone")
    return moment.astimezone(timezone.utc)


def _forbidden_fields(row: Mapping[str, Any]) -> list[str]:
    return sorted(
        name for name in row
        if name in FORBIDDEN_FEATURE_FIELDS or name.startswith("label_")
    )


def build_selective_five_day_panel(
    feature_rows: Iterable[Mapping[str, Any]],
    label_rows: Iterable[Mapping[str, Any]],
    *,
    required_feature_fields: Sequence[str] = (),
) -> list[dict[str, Any]]:
    """Join exact symbol/date keys while blocking future outcome leakage."""
    features = _index_unique(feature_rows, "market_date", "feature")
    labels = _index_unique(label_rows, "decision_date", "label")
    missing = sorted(set(labels) - set(features))
    extra = sorted(set(features) - set(labels))
    if missing or extra:
        raise ValueError(
            f"feature/label keys must match exactly; missing_features={len(missing)} "
            f"extra_features={len(extra)}"
        )

    joined: list[dict[str, Any]] = []
    for key in sorted(labels, key=lambda item: (item[1], item[0])):
        feature = features[key]
        label = labels[key]
        forbidden = _forbidden_fields(feature)
        if forbidden:
            raise ValueError(
                f"feature row contains forbidden outcome fields for {key[0]} {key[1]}: "
                f"{', '.join(forbidden)}"
            )
        missing_required = [name for name in required_feature_fields if name not in feature]
        if missing_required:
            raise ValueError(
                f"feature row missing required fields for {key[0]} {key[1]}: "
                f"{', '.join(missing_required)}"
            )

        decision_day = date.fromisoformat(key[1])
        availability = _utc_moment(feature.get("as_of_utc"), "as_of_utc")
        decision_cutoff = _utc_moment(feature.get("decision_cutoff_utc"), "decision_cutoff_utc")
        if decision_cutoff.date() != decision_day:
            raise ValueError(f"decision cutoff date does not match decision date for {key[0]} {key[1]}")
        if availability > decision_cutoff:
            raise ValueError(f"feature availability is after decision cutoff for {key[0]} {key[1]}")

        entry_day = date.fromisoformat(str(label.get("entry_date") or ""))
        exit_day = date.fromisoformat(str(label.get("exit_date") or ""))
        if not decision_day < entry_day < exit_day:
            raise ValueError(f"label timing is invalid for {key[0]} {key[1]}")

        joined.append({
            **feature,
            **label,
            "symbol": key[0],
            "market_date": key[1],
            "decision_date": key[1],
            "feature_as_of_utc": availability.isoformat(),
            "decision_cutoff_utc": decision_cutoff.isoformat(),
            "research_only": True,
        })
    return joined
