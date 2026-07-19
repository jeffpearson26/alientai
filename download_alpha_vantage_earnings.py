from __future__ import annotations

"""Resumable Alpha Vantage quarterly-earnings collector."""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import requests
from dotenv import load_dotenv

from alientai_v2.data.earnings_history import merge_events, normalize_response


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "data_v2" / "earnings_history" / "earnings_events.jsonl"
DEFAULT_STATE = ROOT / "data_v2" / "earnings_history" / "download_state.json"


def read_symbols(path: Path, limit: int = 0) -> List[str]:
    output: List[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        symbol = line.split(",", 1)[0].strip().upper()
        if symbol and not symbol.startswith("#") and symbol not in output:
            output.append(symbol)
        if limit and len(output) >= limit:
            break
    return output


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def atomic_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def fetch_symbol(symbol: str, api_key: str, timeout: float = 60.0) -> List[Dict[str, Any]]:
    response = requests.get(
        "https://www.alphavantage.co/query",
        params={"function": "EARNINGS", "symbol": symbol, "apikey": api_key},
        timeout=timeout,
    )
    response.raise_for_status()
    return normalize_response(symbol, response.json())


def safe_error(message: Any, api_key: str) -> str:
    """Prevent providers from echoing credentials into logs or state files."""
    cleaned = str(message or "API request failed")
    if api_key:
        cleaned = cleaned.replace(api_key, "[REDACTED]")
    if "rate limit" in cleaned.lower() or "requests per day" in cleaned.lower():
        return "Alpha Vantage daily API rate limit reached; resume on the next allowance window."
    return cleaned[:1000]


def run(
    symbols: Iterable[str], api_key: str, output: Path, state_path: Path,
    delay_seconds: float = 12.5, continue_on_limit: bool = False,
) -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "status": "running",
        "completed_symbols": [],
        "unavailable_symbols": [],
        "failed": [],
    }
    if state_path.exists():
        previous = json.loads(state_path.read_text(encoding="utf-8"))
        state["completed_symbols"] = list(dict.fromkeys(previous.get("completed_symbols", [])))
        state["unavailable_symbols"] = list(
            dict.fromkeys(previous.get("unavailable_symbols", []))
        )
    completed = set(state["completed_symbols"])
    events = read_jsonl(output)
    for symbol in symbols:
        if symbol in completed:
            print(f"SKIP {symbol}")
            continue
        try:
            print(f"FETCH {symbol}")
            rows = fetch_symbol(symbol, api_key)
            events = merge_events(events, rows)
            atomic_jsonl(output, events)
            state["completed_symbols"].append(symbol)
            completed.add(symbol)
            state["event_count"] = len(events)
            state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_json(state_path, state)
            print(f"DONE {symbol}: {len(rows)} quarters; total={len(events)}")
            if delay_seconds > 0:
                time.sleep(delay_seconds)
        except RuntimeError as exc:
            state["status"] = "rate_limited"
            state["failed"].append({"symbol": symbol, "error": safe_error(exc, api_key)})
            state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_json(state_path, state)
            if not continue_on_limit:
                break
        except ValueError as exc:
            if "lacks quarterlyEarnings" not in str(exc):
                raise
            print(f"UNAVAILABLE {symbol}: no quarterly earnings payload")
            state["unavailable_symbols"].append(symbol)
            state["completed_symbols"].append(symbol)
            completed.add(symbol)
            state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_json(state_path, state)
            if delay_seconds > 0:
                time.sleep(delay_seconds)
        except Exception as exc:
            state["failed"].append({"symbol": symbol, "error": safe_error(exc, api_key)})
            state["status"] = "failed_closed"
            state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_json(state_path, state)
            raise
    if state["status"] == "running":
        state["status"] = "complete"
    state["event_count"] = len(events)
    state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    atomic_json(state_path, state)
    return state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols-file", type=Path, default=ROOT / "sp500_expanded_symbols.txt")
    parser.add_argument("--limit-symbols", type=int, default=5)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--delay-seconds", type=float, default=12.5)
    parser.add_argument("--continue-on-limit", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    result = run(
        read_symbols(args.symbols_file, args.limit_symbols), api_key,
        args.output, args.state, args.delay_seconds, args.continue_on_limit,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
