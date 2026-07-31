from __future__ import annotations

"""Capture Schwab option quotes for frozen stock signals; research-only."""

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from alientai_v2.engines.options_research import (
    SCHWAB_CHAIN_URL,
    contract_symbol,
    date_key_to_date,
    safe_float,
    safe_int,
    schwab_get_json,
)
from capture_alpha_vantage_shadow_calls import append_unique, read_jsonl
from shadow_call_options import (
    CallSelectionPolicy,
    OptionChainError,
    conservative_option_return_pct,
    select_call,
)


def fetch_chain(symbol: str, contract: str | None = None) -> dict[str, Any]:
    today = date.today()
    params: dict[str, Any] = {
        "symbol": symbol,
        "contractType": "CALL",
        "includeQuotes": "TRUE",
        "strategy": "SINGLE",
        "fromDate": (today + timedelta(days=14)).isoformat(),
        "toDate": (today + timedelta(days=45)).isoformat(),
    }
    if contract:
        params["symbol"] = contract
    return schwab_get_json(SCHWAB_CHAIN_URL, params)


def normalize_chain(chain: Mapping[str, Any], expected_symbol: str) -> list[dict[str, Any]]:
    symbol = str(chain.get("symbol") or "").upper()
    if symbol and symbol != expected_symbol.upper():
        raise OptionChainError("Schwab chain contains an unexpected underlying")
    rows: list[dict[str, Any]] = []
    expiration_map = chain.get("callExpDateMap")
    if not isinstance(expiration_map, dict):
        raise OptionChainError("Schwab returned no call expiration map")
    for expiration_key, strikes in expiration_map.items():
        expiration = date_key_to_date(str(expiration_key))
        if expiration is None or not isinstance(strikes, dict):
            continue
        for strike_key, contracts in strikes.items():
            if not isinstance(contracts, list):
                continue
            for contract in contracts:
                if not isinstance(contract, dict):
                    continue
                rows.append({
                    "contractID": contract_symbol(contract),
                    "symbol": expected_symbol.upper(),
                    "type": "call",
                    "expiration": expiration.isoformat(),
                    "strike": safe_float(strike_key),
                    "bid": safe_float(contract.get("bid")),
                    "ask": safe_float(contract.get("ask")),
                    "bid_size": safe_int(contract.get("bidSize")),
                    "ask_size": safe_int(contract.get("askSize")),
                    "volume": safe_int(contract.get("totalVolume") or contract.get("volume")),
                    "open_interest": safe_int(contract.get("openInterest")),
                    "implied_volatility": safe_float(
                        contract.get("volatility") or contract.get("impliedVolatility")
                    ),
                    "delta": safe_float(contract.get("delta")),
                    "quote_time": contract.get("quoteTimeInLong"),
                })
    if not rows:
        raise OptionChainError("Schwab returned no call contracts")
    return rows


def capture_entries(args: argparse.Namespace) -> dict[str, Any]:
    signals = [
        row for row in read_jsonl(args.stock_journal)
        if row.get("market_date") == args.market_date and row.get("research_only") is True
    ]
    if not signals:
        raise OptionChainError("no frozen stock signals exist for the requested date")
    captured_at = datetime.now(timezone.utc).isoformat()
    chains: dict[str, list[dict[str, Any]]] = {}
    observations = []
    for signal in signals:
        symbol = str(signal["symbol"]).upper()
        if symbol not in chains:
            chains[symbol] = normalize_chain(fetch_chain(symbol), symbol)
        selected = select_call(chains[symbol], args.market_date, CallSelectionPolicy())
        observations.append({
            "provider": "Schwab",
            "model_id": signal["model_id"],
            "market_date": args.market_date,
            "symbol": symbol,
            "stock_rank": signal["rank"],
            "stock_model_score": signal["model_score"],
            "stock_horizon_minutes": signal["horizon_minutes"],
            "contract_id": selected["contractID"],
            "expiration": selected["expiration"],
            "strike": float(selected["strike"]),
            "delta": selected["delta"],
            "dte": selected["dte"],
            "entry_bid": selected["bid"],
            "entry_ask": selected["ask"],
            "entry_spread_pct": selected["spread_pct"],
            "entry_open_interest": selected["open_interest"],
            "captured_at_utc": captured_at,
            "entry_fill_policy": "buy_at_ask",
            "status": "pending",
            "research_only": True,
            "execution_decision": "AVOID",
        })
    added = append_unique(args.option_journal, observations, ("model_id", "market_date", "symbol"))
    return {"status": "complete", "mode": "entry", "observations": len(observations), "appended": added}


def capture_exits(args: argparse.Namespace) -> dict[str, Any]:
    entries = [
        row for row in read_jsonl(args.option_journal)
        if row.get("market_date") == args.market_date
        and row.get("status") == "pending"
        and int(row.get("stock_horizon_minutes") or 0) == args.horizon_minutes
    ]
    captured_at = datetime.now(timezone.utc).isoformat()
    chains: dict[str, list[dict[str, Any]]] = {}
    outcomes = []
    for entry in entries:
        symbol = str(entry["symbol"]).upper()
        if symbol not in chains:
            chains[symbol] = normalize_chain(fetch_chain(symbol), symbol)
        quote = next(
            (row for row in chains[symbol] if row["contractID"] == entry["contract_id"]),
            None,
        )
        if quote is None:
            raise OptionChainError(f"selected contract unavailable: {entry['contract_id']}")
        exit_bid = float(quote["bid"])
        outcomes.append({
            "provider": "Schwab",
            "model_id": entry["model_id"],
            "market_date": entry["market_date"],
            "symbol": symbol,
            "contract_id": entry["contract_id"],
            "horizon_minutes": args.horizon_minutes,
            "entry_ask": entry["entry_ask"],
            "exit_bid": exit_bid,
            "option_return_pct": conservative_option_return_pct(float(entry["entry_ask"]), exit_bid),
            "captured_at_utc": captured_at,
            "fill_policy": "buy_at_ask_sell_at_bid",
            "research_only": True,
            "execution_decision": "AVOID",
        })
    added = append_unique(
        args.outcome_journal, outcomes,
        ("model_id", "market_date", "symbol", "contract_id", "horizon_minutes"),
    )
    return {"status": "complete", "mode": "exit", "observations": len(outcomes), "appended": added}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("entry", "exit"), required=True)
    parser.add_argument("--market-date", required=True)
    parser.add_argument("--stock-journal", type=Path)
    parser.add_argument("--option-journal", type=Path, required=True)
    parser.add_argument("--outcome-journal", type=Path)
    parser.add_argument("--horizon-minutes", type=int, choices=(20, 60))
    args = parser.parse_args()
    if args.mode == "entry" and args.stock_journal is None:
        parser.error("--stock-journal is required for entry")
    if args.mode == "exit" and (args.outcome_journal is None or args.horizon_minutes is None):
        parser.error("--outcome-journal and --horizon-minutes are required for exit")
    result = capture_entries(args) if args.mode == "entry" else capture_exits(args)
    print(json.dumps({**result, "provider": "Schwab", "research_only": True, "execution_enabled": False}, indent=2))


if __name__ == "__main__":
    main()
