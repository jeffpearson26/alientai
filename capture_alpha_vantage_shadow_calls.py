from __future__ import annotations

"""Capture research-only Alpha Vantage call snapshots; never sends orders."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from alpha_vantage_http import get_alpha_vantage_response
from shadow_call_options import (
    CallSelectionPolicy,
    OptionChainError,
    conservative_option_return_pct,
    select_call,
    validate_realtime_payload,
)


ROOT = Path(__file__).resolve().parent


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_unique(path: Path, rows: list[dict[str, Any]], keys: tuple[str, ...]) -> int:
    existing = {
        tuple(row.get(key) for key in keys) for row in read_jsonl(path)
    } if path.exists() else set()
    additions = [row for row in rows if tuple(row.get(key) for key in keys) not in existing]
    if additions:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            for row in additions:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    return len(additions)


def fetch(api_key: str, symbol: str, contract: str | None = None) -> dict[str, Any]:
    params = {"function": "REALTIME_OPTIONS", "symbol": symbol, "require_greeks": "true"}
    if contract:
        params["contract"] = contract
    return get_alpha_vantage_response(params, api_key, timeout=60).json()


def capture_entries(args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    signals = [
        row for row in read_jsonl(args.stock_journal)
        if row.get("market_date") == args.market_date and row.get("research_only") is True
    ]
    if not signals:
        raise OptionChainError("no frozen stock signals exist for the requested date")
    captured_at = datetime.now(timezone.utc).isoformat()
    observations = []
    for signal in signals:
        symbol = str(signal["symbol"]).upper()
        chain = validate_realtime_payload(fetch(api_key, symbol), symbol)
        selected = select_call(chain, args.market_date, CallSelectionPolicy())
        observations.append({
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


def capture_exits(args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    entries = [
        row for row in read_jsonl(args.option_journal)
        if row.get("market_date") == args.market_date and row.get("status") == "pending"
    ]
    captured_at = datetime.now(timezone.utc).isoformat()
    outcomes = []
    for entry in entries:
        payload = fetch(api_key, str(entry["symbol"]), str(entry["contract_id"]))
        rows = validate_realtime_payload(payload, str(entry["symbol"]))
        row = next((item for item in rows if item["contractID"] == entry["contract_id"]), None)
        if row is None:
            raise OptionChainError(f"selected contract unavailable: {entry['contract_id']}")
        exit_bid = float(row["bid"])
        outcomes.append({
            "model_id": entry["model_id"],
            "market_date": entry["market_date"],
            "symbol": entry["symbol"],
            "contract_id": entry["contract_id"],
            "horizon_minutes": entry["stock_horizon_minutes"],
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
    args = parser.parse_args()
    if args.mode == "entry" and args.stock_journal is None:
        parser.error("--stock-journal is required for entry")
    if args.mode == "exit" and args.outcome_journal is None:
        parser.error("--outcome-journal is required for exit")
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    result = capture_entries(args, api_key) if args.mode == "entry" else capture_exits(args, api_key)
    print(json.dumps({**result, "research_only": True, "execution_enabled": False}, indent=2))


if __name__ == "__main__":
    main()
