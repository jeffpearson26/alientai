from __future__ import annotations

from statistics import mean
from typing import Any, Dict, Iterable, Mapping, Optional


def number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def ratio(numerator: float, denominator: float) -> Optional[float]:
    return numerator / denominator if denominator > 0 else None


def option_chain_features(chain: Iterable[Mapping[str, Any]], stock_price: float) -> Dict[str, Any]:
    calls, puts, liquid = [], [], []
    for option in chain:
        kind = str(option.get("type") or "").lower()
        if kind not in ("call", "put"):
            continue
        (calls if kind == "call" else puts).append(option)
        bid, ask = number(option.get("bid")), number(option.get("ask"))
        mark = (bid + ask) / 2.0
        spread = (ask - bid) / mark if mark > 0 else 999.0
        if bid > 0 and ask > bid and spread <= 0.20 and number(option.get("open_interest")) >= 50:
            liquid.append(option)
    call_volume = sum(number(row.get("volume")) for row in calls)
    put_volume = sum(number(row.get("volume")) for row in puts)
    call_oi = sum(number(row.get("open_interest")) for row in calls)
    put_oi = sum(number(row.get("open_interest")) for row in puts)
    total_volume, total_oi = call_volume + put_volume, call_oi + put_oi
    near_calls, near_puts = [], []
    if stock_price > 0:
        for option in liquid:
            if abs(number(option.get("strike")) / stock_price - 1.0) <= 0.05:
                iv = number(option.get("implied_volatility"), -1.0)
                if iv >= 0:
                    (near_calls if str(option.get("type")).lower() == "call" else near_puts).append(iv)
    call_iv = mean(near_calls) if near_calls else None
    put_iv = mean(near_puts) if near_puts else None
    return {
        "option_chain_available": bool(calls or puts),
        "option_contract_count": len(calls) + len(puts),
        "option_liquid_contract_count": len(liquid),
        "option_call_volume": call_volume,
        "option_put_volume": put_volume,
        "option_call_open_interest": call_oi,
        "option_put_open_interest": put_oi,
        "option_put_call_volume_ratio": ratio(put_volume, call_volume),
        "option_put_call_open_interest_ratio": ratio(put_oi, call_oi),
        "option_volume_open_interest_ratio": ratio(total_volume, total_oi),
        "option_near_money_call_iv": call_iv,
        "option_near_money_put_iv": put_iv,
        "option_near_money_put_call_iv_skew": (put_iv - call_iv) if put_iv is not None and call_iv is not None else None,
    }
