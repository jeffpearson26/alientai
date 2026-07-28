"""Compile one complete, history-aware daily natural-options panel from raw snapshots."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from alientai_v2.features.option_chain_features import option_chain_features
from alientai_v2.research.historical_call_evaluator import chain_path, load_chain
from alientai_v2.research.unusual_call_activity import unusual_call_features
from build_local_schwab_daily_technical_panel import csv_path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def symbols(path: Path) -> list[str]:
    return list(dict.fromkeys(
        line.split(",", 1)[0].strip().upper()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ))


def local_close(daily_dir: Path, symbol: str, market_date: str) -> float | None:
    path = csv_path(daily_dir, symbol)
    if not path.exists():
        return None
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("date") == market_date:
                try:
                    close = float(row["close"])
                    return close if close > 0 else None
                except (KeyError, TypeError, ValueError):
                    return None
    return None


def chain_totals(chain: Iterable[Mapping[str, Any]]) -> tuple[float, float]:
    calls = [row for row in chain if str(row.get("type") or "").lower() == "call"]
    return (
        sum(float(row.get("volume") or 0) for row in calls),
        sum(float(row.get("open_interest") or 0) for row in calls),
    )


def prior_rows(rows: Iterable[Mapping[str, Any]], target_date: str) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        symbol, day = str(row.get("symbol") or "").upper(), str(row.get("market_date") or "")
        if symbol and day < target_date and row.get("option_call_volume") is not None:
            output.append({"symbol": symbol, "market_date": day,
                           "option_call_volume": row.get("option_call_volume"),
                           "option_call_open_interest": row.get("option_call_open_interest")})
    return output


def extension_history(symbol_list: Iterable[str], chains: Path, start_date: str, target_date: str) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    totals, target_chains = [], {}
    for symbol in symbol_list:
        for folder in sorted((chains / target_date[:4]).glob("20??-??-??")):
            day = folder.name
            if not (start_date < day <= target_date):
                continue
            path = chain_path(chains, symbol, day)
            if not path.exists():
                continue
            chain = load_chain(path)
            volume, interest = chain_totals(chain)
            totals.append({"symbol": symbol, "market_date": day, "option_call_volume": volume, "option_call_open_interest": interest})
            if day == target_date:
                target_chains[symbol] = chain
    return totals, target_chains


def compile_panel(
    symbol_list: list[str],
    previous: list[Mapping[str, Any]],
    chains: Path,
    daily_dir: Path,
    target_date: str,
    price_rows: Iterable[Mapping[str, Any]] = (),
) -> tuple[list[dict[str, Any]], list[str]]:
    prior = prior_rows(previous, target_date)
    latest_prior_date = max((str(row["market_date"]) for row in prior), default="")
    if not latest_prior_date or latest_prior_date >= target_date:
        raise ValueError("previous feature history must end before target date")
    extension, target_chains = extension_history(symbol_list, chains, latest_prior_date, target_date)
    history = unusual_call_features([*prior, *extension])
    history_by_key = {(row["symbol"], row["market_date"]): row for row in history}
    prices = {
        (str(row.get("symbol") or "").upper(), str(row.get("market_date") or "")): float(row["close"])
        for row in price_rows
        if row.get("symbol") and row.get("market_date") and row.get("close") is not None
    }
    rows, missing = [], []
    for symbol in symbol_list:
        chain = target_chains.get(symbol)
        close = prices.get((symbol, target_date))
        if close is None:
            close = local_close(daily_dir, symbol, target_date)
        activity = history_by_key.get((symbol, target_date))
        if chain is None or close is None or activity is None:
            missing.append(symbol)
            continue
        rows.append({"symbol": symbol, "market_date": target_date, "source": "alpha_vantage_historical_options",
                     "option_available": True, **option_chain_features(chain, close), **activity})
    return rows, missing


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile a complete natural-options panel for one date.")
    parser.add_argument("--target-date", required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--previous-features", type=Path, required=True)
    parser.add_argument("--chains", type=Path, required=True)
    parser.add_argument("--daily-dir", type=Path, required=True)
    parser.add_argument("--price-panel", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    price_rows = read_jsonl(args.price_panel) if args.price_panel else []
    rows, missing = compile_panel(
        symbols(args.symbols_file), read_jsonl(args.previous_features), args.chains,
        args.daily_dir, args.target_date, price_rows,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({"status": "complete", "research_only": True, "execution_enabled": False,
                      "target_date": args.target_date, "rows": len(rows), "missing": len(missing)}, indent=2))


if __name__ == "__main__":
    main()
