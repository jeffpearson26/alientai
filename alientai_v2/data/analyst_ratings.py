from __future__ import annotations

"""Provider-neutral normalization for event-level analyst rating changes."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Mapping


NORMALIZATION_VERSION = "explicit_labels_v1"
EXPLICIT_LABEL_SCORES = {
    "strong buy": 2.0,
    "buy": 1.0,
    "hold": 0.0,
    "sell": -1.0,
    "strong sell": -2.0,
}
ACTION_MAP = {
    "upgrades": "upgrade", "upgrade": "upgrade",
    "downgrades": "downgrade", "downgrade": "downgrade",
    "initiates": "initiate", "initiate": "initiate",
    "maintains": "maintain", "maintain": "maintain",
    "reiterates": "reiterate", "reiterate": "reiterate",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except (TypeError, ValueError):
        return None


def _iso_utc(value: Any, date: Any = None, time: Any = None) -> str:
    raw = _text(value)
    if not raw and date:
        raw = f"{_text(date)}T{_text(time) or '23:59:59'}"
    if not raw:
        raise ValueError("analyst event requires an announcement timestamp")
    raw = raw.replace("Z", "+00:00")
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def explicit_rating_score(label: Any) -> float | None:
    """Only unambiguous labels are scored; firm-specific wording stays unknown."""
    return EXPLICIT_LABEL_SCORES.get(_text(label).casefold())


def _event_id(provider: str, source_id: str, values: Mapping[str, Any]) -> str:
    if source_id:
        basis = f"{provider}|{source_id}"
    else:
        basis = provider + "|" + json.dumps(values, sort_keys=True, default=str)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def normalize_event(
    *, provider: str, ticker: Any, announcement_timestamp: Any,
    analyst_firm: Any = "", analyst_name: Any = "", action: Any = "",
    old_rating: Any = "", new_rating: Any = "", old_price_target: Any = None,
    new_price_target: Any = None, currency: Any = "USD", source_id: Any = "",
    source_url: Any = "", updated_at: Any = None, raw_payload: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    provider_name = _text(provider).upper()
    symbol = _text(ticker).upper()
    if not provider_name or not symbol:
        raise ValueError("analyst event requires provider and ticker")
    announced = _iso_utc(announcement_timestamp)
    raw_action = _text(action)
    normalized_action = ACTION_MAP.get(raw_action.casefold(), "unknown")
    old_raw = _text(old_rating)
    new_raw = _text(new_rating)
    old_score = explicit_rating_score(old_raw)
    new_score = explicit_rating_score(new_raw)
    score_change = (new_score - old_score) if old_score is not None and new_score is not None else None
    values = {
        "ticker": symbol, "announcement_timestamp_utc": announced,
        "analyst_firm": _text(analyst_firm), "analyst_name": _text(analyst_name),
        "action": raw_action, "old_rating": old_raw, "new_rating": new_raw,
        "old_price_target": _number(old_price_target), "new_price_target": _number(new_price_target),
    }
    return {
        "event_id": _event_id(provider_name, _text(source_id), values),
        **values,
        "provider": provider_name,
        "source_id": _text(source_id),
        "source": _text(source_url) or provider_name,
        "currency": _text(currency).upper() or "USD",
        "normalized_action": normalized_action,
        "old_rating_score": old_score,
        "new_rating_score": new_score,
        "normalized_score_change": score_change,
        "normalization_version": NORMALIZATION_VERSION,
        "updated_at_utc": _iso_utc(updated_at) if updated_at else announced,
        "raw_payload": dict(raw_payload or {}),
    }


def normalize_benzinga(message: Mapping[str, Any]) -> Dict[str, Any]:
    data = message.get("data") if isinstance(message.get("data"), Mapping) else message
    content = data.get("content") if isinstance(data.get("content"), Mapping) else data
    timestamp = data.get("timestamp") or content.get("timestamp")
    if not timestamp:
        timestamp = _iso_utc("", content.get("date"), content.get("time"))
    return normalize_event(
        provider="BENZINGA", ticker=content.get("ticker"), announcement_timestamp=timestamp,
        analyst_firm=content.get("analyst") or content.get("firm"),
        analyst_name=content.get("analyst_name"), action=content.get("action_company"),
        old_rating=content.get("rating_prior"), new_rating=content.get("rating_current"),
        old_price_target=content.get("pt_prior"), new_price_target=content.get("pt_current"),
        currency=content.get("currency") or "USD", source_id=data.get("id") or message.get("id"),
        updated_at=data.get("timestamp"), raw_payload=message,
    )


def normalize_fmp(row: Mapping[str, Any]) -> Dict[str, Any]:
    return normalize_event(
        provider="FMP", ticker=row.get("symbol"),
        announcement_timestamp=row.get("publishedDate") or row.get("date"),
        analyst_firm=row.get("gradingCompany") or row.get("analystCompany"),
        analyst_name=row.get("analyst"), action=row.get("action"),
        old_rating=row.get("previousGrade"), new_rating=row.get("newGrade"),
        old_price_target=row.get("priceTargetPrior"), new_price_target=row.get("priceTarget"),
        currency=row.get("currency") or "USD", source_id=row.get("id"), raw_payload=row,
    )
