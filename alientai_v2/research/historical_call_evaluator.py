from __future__ import annotations

import gzip
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


def number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_chain(path: Path) -> List[Dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    return list(payload.get("data") or [])


def chain_path(root: Path, symbol: str, day: str) -> Path:
    return root / day[:4] / day / f"{symbol}.json.gz"


def eligible_calls(
    chain: Iterable[Mapping[str, Any]], entry_day: date, exit_day: date,
    minimum_open_interest: int = 50, minimum_volume: int = 1,
    maximum_spread_pct: float = 0.20,
) -> List[Mapping[str, Any]]:
    output = []
    minimum_expiry = exit_day + timedelta(days=7)
    maximum_expiry = entry_day + timedelta(days=60)
    for option in chain:
        if str(option.get("type") or "").lower() != "call":
            continue
        try:
            expiration = date.fromisoformat(str(option["expiration"]))
        except (KeyError, ValueError):
            continue
        bid, ask = number(option.get("bid")), number(option.get("ask"))
        mark = (bid + ask) / 2.0
        spread_pct = (ask - bid) / mark if mark > 0 else 999.0
        if not (minimum_expiry <= expiration <= maximum_expiry):
            continue
        if bid <= 0 or ask <= bid or spread_pct > maximum_spread_pct:
            continue
        if number(option.get("open_interest")) < minimum_open_interest:
            continue
        if number(option.get("volume")) < minimum_volume:
            continue
        output.append(option)
    return output


def select_call(
    chain: Sequence[Mapping[str, Any]], stock_price: float, entry_day: date, exit_day: date,
    strategy: str,
) -> Optional[Mapping[str, Any]]:
    candidates = eligible_calls(chain, entry_day, exit_day)
    if not candidates:
        return None
    target_expiry = entry_day + timedelta(days=30)
    if strategy == "atm_30d":
        key = lambda option: (
            abs(number(option.get("strike")) - stock_price) / max(stock_price, 0.01),
            abs((date.fromisoformat(str(option["expiration"])) - target_expiry).days),
            number(option.get("ask")) - number(option.get("bid")),
        )
    elif strategy == "delta60_30d":
        key = lambda option: (
            abs(number(option.get("delta")) - 0.60),
            abs((date.fromisoformat(str(option["expiration"])) - target_expiry).days),
            number(option.get("ask")) - number(option.get("bid")),
        )
    else:
        raise ValueError(f"unsupported strategy: {strategy}")
    return min(candidates, key=key)


def evaluate_trade(
    row: Mapping[str, Any], entry_chain: Sequence[Mapping[str, Any]],
    exit_chain: Sequence[Mapping[str, Any]], strategy: str, commission_per_contract: float = 0.65,
) -> Optional[Dict[str, Any]]:
    entry_day = date.fromisoformat(str(row["market_date"]))
    exit_day = date.fromisoformat(str(row["future_market_date"]))
    selected = select_call(entry_chain, number(row.get("close")), entry_day, exit_day, strategy)
    if selected is None:
        return None
    contract_id = str(selected.get("contractID") or "")
    exit_option = next((option for option in exit_chain if str(option.get("contractID") or "") == contract_id), None)
    if exit_option is None:
        return None
    entry_ask = number(selected.get("ask"))
    exit_bid = number(exit_option.get("bid"))
    if entry_ask <= 0 or exit_bid < 0:
        return None
    entry_cost = entry_ask * 100.0 + commission_per_contract
    exit_value = exit_bid * 100.0 - commission_per_contract
    net_return_pct = (exit_value / entry_cost - 1.0) * 100.0
    return {
        "symbol": str(row["symbol"]), "study_role": str(row.get("study_role") or ""),
        "market_date": str(row["market_date"]), "future_market_date": str(row["future_market_date"]),
        "stock_forward_return_5d_pct": number(row.get("label_forward_return_5d_pct")),
        "strategy": strategy, "contract_id": contract_id, "strike": number(selected.get("strike")),
        "expiration": str(selected.get("expiration")), "entry_ask": entry_ask, "exit_bid": exit_bid,
        "entry_delta": number(selected.get("delta")), "entry_iv": number(selected.get("implied_volatility")),
        "entry_open_interest": int(number(selected.get("open_interest"))),
        "entry_volume": int(number(selected.get("volume"))),
        "net_call_return_pct": net_return_pct,
    }


def metrics(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {"trades": 0}
    returns = [number(row.get("net_call_return_pct")) for row in rows]
    return {
        "trades": len(rows), "symbols": len({str(row["symbol"]) for row in rows}),
        "mean_net_call_return_pct": round(mean(returns), 6),
        "median_net_call_return_pct": round(median(returns), 6),
        "profitable_rate": round(sum(value > 0 for value in returns) / len(returns), 6),
        "total_loss_rate": round(sum(value <= -99 for value in returns) / len(returns), 6),
    }


def summarize(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    groups: Dict[str, List[Mapping[str, Any]]] = {}
    for row in rows:
        key = f"{row['strategy']}|{row['study_role']}"
        groups.setdefault(key, []).append(row)
    return {key: metrics(values) for key, values in sorted(groups.items())}
