from __future__ import annotations

"""Build 17-symbol 1m/5m five-session panels with QQQ/SPY context."""

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from alientai_v2.features.option_chain_features import option_chain_features
from alientai_v2.research.historical_call_evaluator import load_chain
from alientai_v2.research.unusual_call_activity import unusual_call_features
from build_amd_nvda_intraday_five_session_panels import (
    MIN_DAILY_HISTORY,
    ROUND_TRIP_COST_PCT,
    load_symbol,
    make_daily,
    pct,
    resample_regular,
    sha256,
    write_jsonl,
)


RESOLUTIONS = ("1min", "5min")
BENCHMARKS = ("QQQ", "SPY")


def read_universe(path: Path) -> list[str]:
    symbols = [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(symbols) != 17 or len(symbols) != len(set(symbols)):
        raise ValueError("AI/semiconductor universe must contain 17 unique symbols")
    return symbols


def load_from_roots(roots: list[Path], symbol: str) -> pd.DataFrame:
    matches = [root for root in roots if any(root.glob(f"*/*/{symbol}.csv.gz"))]
    if not matches:
        raise ValueError(f"no immutable candle root contains {symbol}")
    frames = [load_symbol(root, symbol) for root in matches]
    output = pd.concat(frames, ignore_index=True).sort_values("timestamp")
    if output["timestamp"].duplicated().any():
        raise ValueError(f"overlapping immutable candle roots for {symbol}")
    return output.reset_index(drop=True)


def daily_lag(rows: list[dict[str, Any]], index: int, sessions: int) -> float | None:
    if index < sessions:
        return None
    return pct(float(rows[index]["close"]), float(rows[index - sessions]["close"]))


def base_features(
    rows: list[dict[str, Any]],
    index: int,
    symbol: str,
    resolution: str,
) -> dict[str, Any]:
    current = rows[index]
    recent_returns = [
        pct(float(rows[pos]["close"]), float(rows[pos - 1]["close"]))
        for pos in range(index - 19, index + 1)
    ]
    recent_high = max(float(row["high"]) for row in rows[index - 19 : index + 1])
    recent_volume = np.asarray(
        [float(row["volume"]) for row in rows[index - 19 : index + 1]]
    )
    return {
        "symbol": symbol,
        "market_date": current["market_date"],
        "close": current["close"],
        **{
            key: value
            for key, value in current.items()
            if key.startswith(f"{resolution}_")
        },
        **{f"symbol_is_{symbol.lower()}": 1.0},
        "daily_return_1d_pct": daily_lag(rows, index, 1),
        "daily_return_5d_pct": daily_lag(rows, index, 5),
        "daily_return_20d_pct": daily_lag(rows, index, 20),
        "daily_return_60d_pct": daily_lag(rows, index, 60),
        "daily_realized_volatility_20d_pct": float(
            np.std(recent_returns, ddof=0)
        ),
        "daily_pullback_from_20d_high_pct": pct(
            float(current["close"]), recent_high
        ),
        "daily_volume_vs_20d_mean": (
            float(current["volume"]) / float(recent_volume.mean())
            if recent_volume.mean() > 0 else None
        ),
        "resolution": resolution,
        "research_only": True,
        "execution_enabled": False,
    }


def benchmark_context(
    rows: list[dict[str, Any]],
    resolution: str,
) -> dict[str, dict[str, Any]]:
    output = {}
    for index in range(MIN_DAILY_HISTORY, len(rows)):
        current = rows[index]
        output[str(current["market_date"])] = {
            "session_return_pct": current[f"{resolution}_session_return_pct"],
            "return_1d_pct": daily_lag(rows, index, 1),
            "return_5d_pct": daily_lag(rows, index, 5),
            "return_20d_pct": daily_lag(rows, index, 20),
            "realized_volatility_20d_pct": float(
                np.std(
                    [
                        pct(
                            float(rows[pos]["close"]),
                            float(rows[pos - 1]["close"]),
                        )
                        for pos in range(index - 19, index + 1)
                    ],
                    ddof=0,
                )
            ),
        }
    return output


def attach_benchmarks(
    row: dict[str, Any],
    contexts: dict[str, dict[str, dict[str, Any]]],
    resolution: str,
) -> bool:
    market_date = str(row["market_date"])
    for benchmark in BENCHMARKS:
        values = contexts[benchmark].get(market_date)
        if values is None:
            return False
        prefix = benchmark.lower()
        for name, value in values.items():
            row[f"{prefix}_{name}"] = value
        row[f"relative_to_{prefix}_session_pct"] = (
            float(row[f"{resolution}_session_return_pct"])
            - float(values["session_return_pct"])
        )
        for sessions in (1, 5, 20):
            stock_value = row[f"daily_return_{sessions}d_pct"]
            benchmark_value = values[f"return_{sessions}d_pct"]
            row[f"relative_to_{prefix}_{sessions}d_pct"] = (
                float(stock_value) - float(benchmark_value)
                if stock_value is not None and benchmark_value is not None
                else None
            )
    return True


def all_option_features(
    roots: list[Path],
    symbols: list[str],
    closes: dict[tuple[str, str], float],
) -> dict[tuple[str, str], dict[str, Any]]:
    base: dict[tuple[str, str], dict[str, Any]] = {}
    for root in roots:
        for symbol in symbols:
            for path in sorted(root.glob(f"*/*/{symbol}.json.gz")):
                market_date = path.parent.name
                key = (symbol, market_date)
                if key in base:
                    raise ValueError(f"duplicate option chain across roots: {key}")
                chain = load_chain(path)
                stock_price = closes.get(key)
                if not chain or stock_price is None or stock_price <= 0:
                    continue
                features = option_chain_features(chain, stock_price)
                if features["option_chain_available"]:
                    base[key] = {
                        "symbol": symbol,
                        "market_date": market_date,
                        **features,
                    }
    rolling = unusual_call_features(base.values())
    return {
        (str(row["symbol"]), str(row["market_date"])): {
            "call_features_available": True,
            **{
                name: value
                for name, value in base[
                    (str(row["symbol"]), str(row["market_date"]))
                ].items()
                if name.startswith("option_call_")
                or name.startswith("option_near_money_call_")
                or name
                in {
                    "option_contract_count",
                    "option_liquid_contract_count",
                }
            },
            **{
                name: value
                for name, value in row.items()
                if name not in {"symbol", "market_date"}
            },
        }
        for row in rolling
    }


def missing_call_fields() -> dict[str, Any]:
    return {
        "call_features_available": False,
        "call_activity_history_count": None,
        "call_volume_vs_prior_median": None,
        "call_volume_zscore": None,
        "call_volume_unusual": None,
        "call_volume_open_interest_ratio": None,
        "option_call_volume": None,
        "option_call_open_interest": None,
        "option_near_money_call_iv": None,
        "option_contract_count": None,
        "option_liquid_contract_count": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--candle-root", type=Path, action="append", required=True)
    parser.add_argument("--options-root", type=Path, action="append", required=True)
    parser.add_argument("--prospective-date", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    symbols = read_universe(args.universe)
    all_symbols = symbols + list(BENCHMARKS)
    raw = {
        symbol: load_from_roots(args.candle_root, symbol)
        for symbol in all_symbols
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for resolution in RESOLUTIONS:
        daily = {
            symbol: make_daily(resample_regular(frame, resolution), resolution)
            for symbol, frame in raw.items()
        }
        closes = {
            (symbol, str(row["market_date"])): float(row["close"])
            for symbol in symbols
            for row in daily[symbol]
        }
        calls = all_option_features(args.options_root, symbols, closes)
        contexts = {
            benchmark: benchmark_context(daily[benchmark], resolution)
            for benchmark in BENCHMARKS
        }
        labelled, prospective = [], []
        for symbol in symbols:
            rows = daily[symbol]
            for index in range(MIN_DAILY_HISTORY, len(rows)):
                row = base_features(rows, index, symbol, resolution)
                for universe_symbol in symbols:
                    row[f"symbol_is_{universe_symbol.lower()}"] = float(
                        symbol == universe_symbol
                    )
                if not attach_benchmarks(row, contexts, resolution):
                    continue
                row.update(calls.get((symbol, row["market_date"]), missing_call_fields()))
                if index + 5 < len(rows):
                    entry, exit_row = rows[index + 1], rows[index + 5]
                    gross = pct(float(exit_row["close"]), float(entry["open"]))
                    labelled.append(
                        {
                            **row,
                            "label_entry_market_date": entry["market_date"],
                            "label_5d_exit_market_date": exit_row["market_date"],
                            "label_5d_gross_return_pct": gross,
                            "label_5d_net_return_pct": gross
                            - ROUND_TRIP_COST_PCT,
                            "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
                            "label_contract": (
                                "decision after completed prior regular session; "
                                "entry next open; exit fifth subsequent close"
                            ),
                        }
                    )
                if row["market_date"] == args.prospective_date:
                    prospective.append(row)
        labelled.sort(key=lambda row: (row["market_date"], row["symbol"]))
        prospective.sort(key=lambda row: row["symbol"])
        panel_path = args.output_root / f"ai17_{resolution}_five_session_panel.jsonl"
        prospective_path = (
            args.output_root
            / f"ai17_{resolution}_{args.prospective_date}_prospective.jsonl"
        )
        write_jsonl(panel_path, labelled)
        write_jsonl(prospective_path, prospective)
        outputs[resolution] = {
            "panel": str(panel_path),
            "panel_sha256": sha256(panel_path),
            "rows": len(labelled),
            "first_date": min(row["market_date"] for row in labelled),
            "last_date": max(row["market_date"] for row in labelled),
            "call_rows": sum(bool(row["call_features_available"]) for row in labelled),
            "unusual_call_rows": sum(
                row["call_volume_unusual"] is True for row in labelled
            ),
            "prospective": str(prospective_path),
            "prospective_sha256": sha256(prospective_path),
            "prospective_rows": len(prospective),
            "prospective_call_rows": sum(
                bool(row["call_features_available"]) for row in prospective
            ),
        }
    manifest = {
        "status": "complete",
        "symbols": symbols,
        "benchmarks": list(BENCHMARKS),
        "resolutions": list(RESOLUTIONS),
        "prospective_date": args.prospective_date,
        "prior_session_option_contract": True,
        "outputs": outputs,
        "research_only": True,
        "execution_enabled": False,
    }
    path = args.output_root / "panel_manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
