"""Archive a source-pure full-universe Schwab call-volume observation.

This collector exists only to build the ten-prior-session Schwab history needed
for a future contextual unusual-call fallback.  It does not score candidates,
place orders, modify settings, or combine Schwab volumes with Alpha Vantage
history.
"""
from __future__ import annotations

import argparse
import gzip
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from alientai_v2.engines.options_research import SCHWAB_CHAIN_URL, schwab_get_json
from capture_schwab_shadow_calls import normalize_chain
from download_alpha_vantage_historical_options import atomic_json, replace_with_retry
from download_alpha_vantage_option_panel import read_symbols
from refresh_schwab_token_standalone import refresh_token


def summarize_chain(payload: Mapping[str, Any], symbol: str, market_date: str) -> dict[str, Any]:
    rows = normalize_chain(payload, symbol)
    volume = sum(int(row.get("volume") or 0) for row in rows)
    open_interest = sum(int(row.get("open_interest") or 0) for row in rows)
    return {
        "symbol": symbol.upper(),
        "market_date": market_date,
        "source": "schwab_option_chain",
        "option_call_volume": volume,
        "option_call_open_interest": open_interest,
        "call_contracts": len(rows),
        "underlying_price": float(payload.get("underlyingPrice") or 0),
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "execution_enabled": False,
    }


def archive_path(output: Path, symbol: str, market_date: str) -> Path:
    safe = "".join(char for char in symbol if char.isalnum() or char in ".-")
    return output / market_date[:4] / market_date / f"{safe}.json.gz"


def write_gzip(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=6) as handle:
        json.dump(value, handle, separators=(",", ":"))
    replace_with_retry(temporary, path)


def fetch(symbol: str) -> dict[str, Any]:
    return schwab_get_json(
        SCHWAB_CHAIN_URL,
        {
            "symbol": symbol,
            "contractType": "CALL",
            "includeQuotes": "TRUE",
            "strategy": "SINGLE",
        },
    )


def fetch_with_refresh(symbol: str) -> dict[str, Any]:
    try:
        return fetch(symbol)
    except RuntimeError as exc:
        if "401 unauthorized" not in str(exc).lower():
            raise
        refresh_token()
        return fetch(symbol)


def write_summary(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in sorted(rows, key=lambda item: str(item["symbol"])):
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")
    replace_with_retry(temporary, path)


def run(
    symbol_list: list[str],
    market_date: str,
    output: Path,
    delay_seconds: float = 0.1,
) -> dict[str, Any]:
    manifest_path = output / "manifest.json"
    manifest: dict[str, Any] = {
        "status": "running",
        "market_date": market_date,
        "source": "Schwab",
        "research_only": True,
        "execution_enabled": False,
        "requested": symbol_list,
        "completed": [],
        "unavailable": [],
        "failed": [],
        "rows": [],
    }
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        if str(previous.get("market_date") or "") != market_date:
            raise ValueError("existing manifest belongs to another market date")
        for field in ("completed", "unavailable", "rows"):
            manifest[field] = list(previous.get(field) or [])
    completed = set(manifest["completed"])
    unavailable = set(manifest["unavailable"])
    rows_by_symbol = {
        str(row.get("symbol") or "").upper(): row
        for row in manifest["rows"]
        if isinstance(row, Mapping)
    }

    for index, symbol in enumerate(symbol_list, start=1):
        if symbol in completed or symbol in unavailable:
            continue
        try:
            payload = fetch_with_refresh(symbol)
            row = summarize_chain(payload, symbol, market_date)
            write_gzip(archive_path(output, symbol, market_date), payload)
            rows_by_symbol[symbol] = row
            manifest["completed"].append(symbol)
            completed.add(symbol)
            print(
                f"[{index}/{len(symbol_list)}] {symbol}: "
                f"{row['call_contracts']} calls, volume={row['option_call_volume']}",
                flush=True,
            )
        except Exception as exc:
            text = str(exc)
            if "no call expiration map" in text.lower() or "no call contracts" in text.lower():
                manifest["unavailable"].append(symbol)
                unavailable.add(symbol)
                print(f"[{index}/{len(symbol_list)}] {symbol}: UNAVAILABLE", flush=True)
            else:
                manifest["status"] = "failed_closed"
                manifest["failed"].append({"symbol": symbol, "error": text[:500]})
                manifest["rows"] = list(rows_by_symbol.values())
                manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
                atomic_json(manifest_path, manifest)
                raise
        manifest["rows"] = list(rows_by_symbol.values())
        manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_json(manifest_path, manifest)
        if delay_seconds:
            time.sleep(delay_seconds)

    manifest["rows"] = list(rows_by_symbol.values())
    manifest["status"] = "complete"
    manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    atomic_json(manifest_path, manifest)
    write_summary(output / f"schwab_call_volume_{market_date}.jsonl", manifest["rows"])
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Archive a full-universe Schwab call-volume panel."
    )
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--market-date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--delay-seconds", type=float, default=0.1)
    parser.add_argument("--limit-symbols", type=int, default=0)
    args = parser.parse_args()
    symbol_list = read_symbols(args.symbols_file)
    if args.limit_symbols:
        symbol_list = symbol_list[: args.limit_symbols]
    result = run(symbol_list, args.market_date, args.output, args.delay_seconds)
    print(
        json.dumps(
            {
                "status": result["status"],
                "requested": len(result["requested"]),
                "completed": len(result["completed"]),
                "unavailable": len(result["unavailable"]),
                "failed": len(result["failed"]),
                "research_only": True,
                "execution_enabled": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
