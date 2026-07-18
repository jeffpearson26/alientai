from __future__ import annotations

"""Chronological RCEF research-row construction with five-day outcomes."""

from datetime import date, datetime, time, timezone
from statistics import pstdev
from typing import Any, Dict, Iterable, List, Mapping, Sequence
from zoneinfo import ZoneInfo

from alientai_v2.features.insider_purchase_features import build_insider_purchase_features, safe_float
from alientai_v2.features.technical_snapshot import build_technical_snapshot


EASTERN = ZoneInfo("America/New_York")


def candle_date(row: Mapping[str, Any]) -> date:
    raw = str(row.get("date") or row.get("datetime_utc") or "").strip()
    if raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(raw[:10])
            except ValueError:
                pass
    milliseconds = int(safe_float(row.get("datetime_ms")))
    if milliseconds:
        return datetime.fromtimestamp(milliseconds / 1000.0, tz=timezone.utc).date()
    raise ValueError("daily candle requires date or timestamp")


def market_close_utc(day: date) -> datetime:
    return datetime.combine(day, time(16, 0), tzinfo=EASTERN).astimezone(timezone.utc)


def return_pct(old: float, new: float) -> float:
    return ((new / old) - 1.0) * 100.0 if old > 0 and new > 0 else 0.0


def canonical_candles(rows: Iterable[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    by_day: Dict[date, Mapping[str, Any]] = {}
    for row in rows:
        close = safe_float(row.get("close"))
        if close > 0:
            by_day[candle_date(row)] = row
    return [by_day[day] for day in sorted(by_day)]


def build_research_rows(
    *, symbol: str, candles: Sequence[Mapping[str, Any]],
    benchmark_candles: Sequence[Mapping[str, Any]], sec_purchases: Sequence[Mapping[str, Any]] = (),
    horizon_days: int = 5, minimum_history: int = 60,
) -> List[Dict[str, Any]]:
    if horizon_days <= 0 or minimum_history < 21:
        raise ValueError("invalid horizon or history")
    stock = canonical_candles(candles)
    benchmark_by_day = {candle_date(row): row for row in canonical_candles(benchmark_candles)}
    output: List[Dict[str, Any]] = []
    for index in range(minimum_history - 1, len(stock) - horizon_days):
        current = stock[index]
        future = stock[index + horizon_days]
        day = candle_date(current)
        future_day = candle_date(future)
        benchmark_now = benchmark_by_day.get(day)
        benchmark_future = benchmark_by_day.get(future_day)
        if benchmark_now is None or benchmark_future is None:
            continue
        closes = [safe_float(row.get("close")) for row in stock[index - 59:index + 1]]
        daily_returns = [return_pct(closes[i - 1], closes[i]) for i in range(1, len(closes))]
        current_close = closes[-1]
        future_return = return_pct(current_close, safe_float(future.get("close")))
        benchmark_return = return_pct(
            safe_float(benchmark_now.get("close")), safe_float(benchmark_future.get("close"))
        )
        as_of = market_close_utc(day)
        insider = build_insider_purchase_features(sec_purchases, symbol, as_of)
        row: Dict[str, Any] = {
            "symbol": str(symbol).upper(), "as_of_utc": as_of.isoformat(),
            "market_date": day.isoformat(), "future_market_date": future_day.isoformat(),
            "close": current_close,
            "return_5d_lag_pct": return_pct(closes[-6], closes[-1]),
            "return_20d_lag_pct": return_pct(closes[-21], closes[-1]),
            "return_60d_lag_pct": return_pct(closes[0], closes[-1]),
            "realized_volatility_20d_pct": pstdev(daily_returns[-20:]) if len(daily_returns) >= 20 else 0.0,
            "label_forward_return_5d_pct": future_return,
            "label_benchmark_return_5d_pct": benchmark_return,
            "label_excess_return_5d_pct": future_return - benchmark_return,
            "label_up_2pct": future_return >= 2.0,
        }
        row.update(insider)
        row.update(build_technical_snapshot(stock[index - 59:index + 1]))
        output.append(row)
    return output
