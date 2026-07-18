from __future__ import annotations

"""Leakage-safe features from normalized SEC Form 4 code-P purchases."""

from datetime import datetime, timezone
from math import log1p
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if number == number else default
    except (TypeError, ValueError):
        return default


def timestamp(value: Any) -> datetime:
    raw = str(value or "").strip().replace("Z", "+00:00")
    if not raw:
        raise ValueError("timestamp is required")
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def economic_identity(row: Mapping[str, Any]) -> Tuple[Any, ...]:
    """Identify the economic trade so amendments do not become extra buys."""
    return (
        str(row.get("ticker") or "").upper().strip(),
        str(row.get("insider_name") or "").casefold().strip(),
        str(row.get("transaction_date") or ""),
        round(safe_float(row.get("shares")), 6),
        round(safe_float(row.get("price")), 6),
        str(row.get("ownership_type") or "").upper().strip(),
    )


def visible_purchases(
    rows: Iterable[Mapping[str, Any]], symbol: str, as_of: Any,
) -> List[Mapping[str, Any]]:
    cutoff = timestamp(as_of)
    wanted = str(symbol or "").upper().strip()
    latest_by_trade: Dict[Tuple[Any, ...], Mapping[str, Any]] = {}
    for row in rows:
        if str(row.get("ticker") or "").upper().strip() != wanted:
            continue
        if str(row.get("transaction_code") or "").upper() != "P":
            continue
        if not bool(row.get("is_training_eligible", True)):
            continue
        try:
            available = timestamp(row.get("available_at_utc") or row.get("filing_timestamp_utc"))
        except ValueError:
            continue
        if available > cutoff:
            continue
        identity = economic_identity(row)
        previous = latest_by_trade.get(identity)
        if previous is None or timestamp(previous.get("available_at_utc")) < available:
            latest_by_trade[identity] = row
    return sorted(latest_by_trade.values(), key=lambda row: timestamp(row.get("available_at_utc")))


def _window(rows: Sequence[Mapping[str, Any]], cutoff: datetime, days: int) -> List[Mapping[str, Any]]:
    return [
        row for row in rows
        if 0.0 <= (cutoff - timestamp(row.get("available_at_utc"))).total_seconds() / 86400.0 <= days
    ]


def _total_value(row: Mapping[str, Any]) -> float:
    explicit = safe_float(row.get("total_value"))
    return explicit if explicit > 0.0 else safe_float(row.get("shares")) * safe_float(row.get("price"))


def build_insider_purchase_features(
    rows: Iterable[Mapping[str, Any]], symbol: str, as_of: Any,
) -> Dict[str, Any]:
    cutoff = timestamp(as_of)
    visible = visible_purchases(rows, symbol, cutoff)
    windows = {days: _window(visible, cutoff, days) for days in (7, 30, 90)}
    features: Dict[str, Any] = {
        "insider_purchase_available": bool(visible),
        "insider_purchase_total_visible": len(visible),
    }
    for days, selected in windows.items():
        values = [_total_value(row) for row in selected]
        insiders = {str(row.get("insider_name") or "").casefold().strip() for row in selected if row.get("insider_name")}
        features[f"insider_purchase_count_{days}d"] = len(selected)
        features[f"insider_unique_buyers_{days}d"] = len(insiders)
        features[f"insider_total_value_{days}d"] = round(sum(values), 2)
        features[f"insider_log_total_value_{days}d"] = round(log1p(max(0.0, sum(values))), 8)
        features[f"insider_max_purchase_value_{days}d"] = round(max(values, default=0.0), 2)

    recent = windows[30]
    features["insider_officer_buy_count_30d"] = sum(bool(row.get("is_officer")) for row in recent)
    features["insider_director_buy_count_30d"] = sum(bool(row.get("is_director")) for row in recent)
    features["insider_ten_percent_owner_buy_count_30d"] = sum(bool(row.get("is_ten_percent_owner")) for row in recent)
    features["insider_cluster_buy_30d"] = features["insider_unique_buyers_30d"] >= 2
    features["insider_large_purchase_30d"] = features["insider_max_purchase_value_30d"] >= 100_000.0

    ownership_increases = []
    for row in recent:
        shares = safe_float(row.get("shares"))
        after = safe_float(row.get("shares_owned_after"))
        before = after - shares
        if shares > 0.0 and before > 0.0:
            ownership_increases.append(shares / before)
    features["insider_max_ownership_increase_ratio_30d"] = round(max(ownership_increases, default=0.0), 8)
    if visible:
        age = (cutoff - timestamp(visible[-1].get("available_at_utc"))).total_seconds() / 86400.0
        features["insider_days_since_latest_purchase"] = round(max(0.0, age), 6)
    else:
        features["insider_days_since_latest_purchase"] = None
    return features


def fetch_symbol_purchases(client: Any, symbol: str, as_of: Any, lookback_days: int = 90) -> List[Dict[str, Any]]:
    """Fetch only training-eligible rows visible by as_of from Supabase."""
    cutoff = timestamp(as_of)
    lower = cutoff.timestamp() - max(1, lookback_days) * 86400
    lower_iso = datetime.fromtimestamp(lower, tz=timezone.utc).isoformat()
    response = (
        client.table("v2_sec_form4_purchases")
        .select("*")
        .eq("ticker", str(symbol).upper().strip())
        .eq("is_training_eligible", True)
        .gte("available_at_utc", lower_iso)
        .lte("available_at_utc", cutoff.isoformat())
        .order("available_at_utc")
        .execute()
    )
    return list(response.data or [])
