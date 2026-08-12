"""Resumable Alpha Vantage compact-daily collector for paper-signal preparation."""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from alpha_vantage_http import get_alpha_vantage_response
from download_alpha_vantage_option_panel import read_symbols


ROOT = Path(__file__).resolve().parent


def fetch(
    symbol: str,
    api_key: str,
    outputsize: str = "compact",
    function: str = "TIME_SERIES_DAILY",
) -> dict:
    response = get_alpha_vantage_response(
        {"function": function, "symbol": symbol, "outputsize": outputsize},
        api_key,
        timeout=90,
    )
    payload = response.json()
    if not isinstance(payload, dict) or not any(str(key).startswith("Time Series") for key in payload):
        message = payload.get("Error Message") or payload.get("Note") or payload.get("Information")
        raise RuntimeError(str(message or "daily response contained no time series"))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect a resumable natural-universe compact daily panel.")
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--delay-seconds", type=float, default=0.75)
    parser.add_argument("--outputsize", choices=("compact", "full"), default="compact")
    parser.add_argument(
        "--function",
        choices=("TIME_SERIES_DAILY", "TIME_SERIES_DAILY_ADJUSTED"),
        default="TIME_SERIES_DAILY",
    )
    parser.add_argument(
        "--symbol-aliases",
        type=Path,
        help="Optional JSON mapping frozen universe symbols to provider symbols.",
    )
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    args.output.mkdir(parents=True, exist_ok=True)
    aliases = (
        {
            str(key).upper(): str(value).upper()
            for key, value in json.loads(
                args.symbol_aliases.read_text(encoding="utf-8")
            ).items()
        }
        if args.symbol_aliases
        else {}
    )
    completed, failed = [], {}
    for index, symbol in enumerate(read_symbols(args.symbols_file), 1):
        path = args.output / f"{symbol.replace('/', '-').replace('.', '-')}_daily.json"
        if path.exists():
            completed.append(symbol)
            continue
        try:
            provider_symbol = aliases.get(symbol, symbol)
            payload = fetch(provider_symbol, api_key, args.outputsize, args.function)
            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            temporary.replace(path)
            completed.append(symbol)
            print(f"[{index}] {symbol}: saved", flush=True)
        except Exception as exc:
            failed[symbol] = str(exc)
            print(f"[{index}] {symbol}: ERROR {exc}", flush=True)
        if args.delay_seconds > 0:
            time.sleep(args.delay_seconds)
    manifest = {
        "status": "complete" if not failed else "partial",
        "completed": completed,
        "failed": failed,
        "function": args.function,
        "outputsize": args.outputsize,
        "source_symbol_aliases": aliases,
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "completed": len(completed), "failed": len(failed)}))


if __name__ == "__main__":
    main()
