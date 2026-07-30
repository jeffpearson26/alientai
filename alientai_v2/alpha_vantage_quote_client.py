"""Native Alpha Vantage quote client for the active AlienTAI paper engine."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

from alpha_vantage_http import get_alpha_vantage_response, redact_sensitive_text
from alientai_v2.utils import PROJECT_ROOT, safe_float


MAX_BULK_SYMBOLS = 100


def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index:index + size]


def _number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, str):
        value = value.replace(",", "").replace("%", "").strip()
    return safe_float(value, default)


def _quote_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for name in ("data", "quotes", "realtime_quotes", "Realtime Bulk Quotes"):
        rows = payload.get(name)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def parse_bulk_quote_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize provider rows into the stable quote schema used by engines."""
    rows = _quote_rows(payload)
    if not rows:
        message = payload.get("Error Message") or payload.get("Note") or payload.get("Information")
        raise RuntimeError(str(message or "Alpha Vantage bulk quote response contained no quote rows"))

    normalized: list[dict[str, Any]] = []
    for raw in rows:
        symbol = str(raw.get("symbol") or raw.get("ticker") or "").strip().upper()
        price = _number(raw.get("price") or raw.get("close") or raw.get("last") or raw.get("last_price"))
        if not symbol or price <= 0:
            continue
        previous_close = _number(raw.get("previous_close") or raw.get("previousClose"))
        net_change_percent = _number(
            raw.get("change_percent") or raw.get("change_percentage") or raw.get("percent_change")
        )
        if not net_change_percent and previous_close > 0:
            net_change_percent = ((price / previous_close) - 1.0) * 100.0
        bid = _number(raw.get("bid") or raw.get("bid_price"))
        ask = _number(raw.get("ask") or raw.get("ask_price"))
        spread_percent = 0.25
        if bid > 0 and ask >= bid:
            midpoint = (bid + ask) / 2.0
            spread_percent = ((ask - bid) / midpoint) * 100.0 if midpoint > 0 else 99.0
        normalized.append({
            "symbol": symbol,
            "price": round(price, 4),
            "net_change_percent": round(net_change_percent, 4),
            "relative_volume": round(_number(raw.get("relative_volume"), 1.0), 4),
            "spread_percent": round(spread_percent, 4),
            "volume": _number(raw.get("volume")),
            "bid": bid,
            "ask": ask,
            "close": previous_close,
            "timestamp": raw.get("timestamp") or raw.get("latest_trading_day"),
            "source": "alpha_vantage_realtime_bulk_quote",
        })
    if not normalized:
        raise RuntimeError("Alpha Vantage bulk quote response contained no usable prices")
    return normalized


def _api_key() -> str:
    load_dotenv(Path(PROJECT_ROOT) / ".env")
    key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required for active paper-engine quotes")
    return key


def get_real_v2_quotes(symbols: list[str]) -> list[dict[str, Any]]:
    """Fetch up to 100 US quotes per provider request using the premium bulk API."""
    requested = list(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))
    if not requested:
        return []
    api_key = _api_key()
    quotes: dict[str, dict[str, Any]] = {}
    for batch in _chunks(requested, MAX_BULK_SYMBOLS):
        response = get_alpha_vantage_response(
            {"function": "REALTIME_BULK_QUOTES", "symbol": ",".join(batch)},
            api_key,
            timeout=90,
        )
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Alpha Vantage bulk quote response was not an object")
        try:
            parsed = parse_bulk_quote_payload(payload)
        except Exception as exc:
            raise RuntimeError(redact_sensitive_text(exc, api_key)) from None
        quotes.update({row["symbol"]: row for row in parsed})
    return [quotes[symbol] for symbol in requested if symbol in quotes]
