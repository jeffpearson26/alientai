from __future__ import annotations

"""Build the point-in-time Nasdaq-101 six-month technical research panel."""

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from alientai_v2.research.long_horizon_technicals import (
    long_horizon_technical_features,
)
from build_nasdaq_qqq_spy_60session_panel import load_adjusted_daily


HORIZON_SESSIONS = 126
MIN_HISTORY = 126
TECHNICAL_WINDOW = 253
ROUND_TRIP_COST_PCT = 0.25
BENCHMARKS = ("QQQ", "SPY")
RELATIVE_WINDOWS = (20, 60, 126, 252)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_candidates(path: Path) -> list[str]:
    symbols = [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(symbols) != 101 or len(symbols) != len(set(symbols)):
        raise ValueError("expected exactly 101 unique Nasdaq securities")
    if set(symbols) & set(BENCHMARKS):
        raise ValueError("QQQ/SPY must be context-only, not candidates")
    return symbols


def pct_change(current: float, prior: float) -> float:
    return (current / prior - 1.0) * 100.0


def lag_return(
    rows: Sequence[Mapping[str, Any]], index: int, sessions: int
) -> float | None:
    if index < sessions:
        return None
    return pct_change(
        float(rows[index]["close"]), float(rows[index - sessions]["close"])
    )


def beta_and_correlation(
    stock_rows: Sequence[Mapping[str, Any]],
    stock_index: int,
    benchmark_rows: Sequence[Mapping[str, Any]],
    benchmark_index: int,
    sessions: int,
) -> tuple[float | None, float | None]:
    if stock_index < sessions or benchmark_index < sessions:
        return None, None
    stock = np.asarray(
        [
            np.log(
                float(stock_rows[position]["close"])
                / float(stock_rows[position - 1]["close"])
            )
            for position in range(stock_index - sessions + 1, stock_index + 1)
        ],
        dtype=float,
    )
    benchmark = np.asarray(
        [
            np.log(
                float(benchmark_rows[position]["close"])
                / float(benchmark_rows[position - 1]["close"])
            )
            for position in range(
                benchmark_index - sessions + 1, benchmark_index + 1
            )
        ],
        dtype=float,
    )
    benchmark_variance = float(np.var(benchmark))
    if benchmark_variance <= 0.0:
        return None, None
    beta = float(np.cov(stock, benchmark, ddof=0)[0, 1] / benchmark_variance)
    if float(np.std(stock)) <= 0.0 or float(np.std(benchmark)) <= 0.0:
        correlation = None
    else:
        correlation = float(np.corrcoef(stock, benchmark)[0, 1])
    return beta, correlation


def benchmark_context(
    prefix: str,
    rows: Sequence[Mapping[str, Any]],
    index: int,
) -> dict[str, Any]:
    features = long_horizon_technical_features(
        rows[max(0, index + 1 - TECHNICAL_WINDOW) : index + 1]
    )
    return {
        name.replace("technical_", f"{prefix}_technical_", 1)
        .replace("lh_", f"{prefix}_lh_", 1): value
        for name, value in features.items()
    }


def build_rows(
    daily: Mapping[str, list[dict[str, Any]]],
    candidates: Sequence[str],
    start_date: str,
    workers: int = 1,
    decision_stride: int = 1,
    horizon_sessions: int = HORIZON_SESSIONS,
) -> list[dict[str, Any]]:
    benchmark_maps = {
        symbol: {
            row["market_date"]: index
            for index, row in enumerate(daily[symbol])
        }
        for symbol in BENCHMARKS
    }
    common_dates = sorted(
        set(benchmark_maps["QQQ"]) & set(benchmark_maps["SPY"])
    )
    calendar_index = {market_date: index for index, market_date in enumerate(common_dates)}
    benchmark_cache: dict[str, dict[str, Any]] = {}
    for market_date in common_dates:
        qqq_index = benchmark_maps["QQQ"][market_date]
        spy_index = benchmark_maps["SPY"][market_date]
        if min(qqq_index, spy_index) < MIN_HISTORY - 1:
            continue
        benchmark_cache[market_date] = {
            **benchmark_context("qqq", daily["QQQ"], qqq_index),
            **benchmark_context("spy", daily["SPY"], spy_index),
        }

    def build_symbol(symbol: str) -> list[dict[str, Any]]:
        symbol_output: list[dict[str, Any]] = []
        candles = daily[symbol]
        for index in range(MIN_HISTORY - 1, len(candles) - horizon_sessions):
            decision = candles[index]
            market_date = str(decision["market_date"])
            if market_date < start_date or market_date not in benchmark_cache:
                continue
            if calendar_index[market_date] % decision_stride != 0:
                continue
            if any(market_date not in benchmark_maps[name] for name in BENCHMARKS):
                continue
            entry = candles[index + 1]
            exit_row = candles[index + horizon_sessions]
            features = long_horizon_technical_features(
                candles[max(0, index + 1 - TECHNICAL_WINDOW) : index + 1]
            )
            relative: dict[str, Any] = {}
            for benchmark in BENCHMARKS:
                benchmark_rows = daily[benchmark]
                benchmark_index = benchmark_maps[benchmark][market_date]
                for window in RELATIVE_WINDOWS:
                    stock_return = lag_return(candles, index, window)
                    benchmark_return = lag_return(
                        benchmark_rows, benchmark_index, window
                    )
                    relative[
                        f"relative_to_{benchmark.lower()}_{window}d_pct"
                    ] = (
                        stock_return - benchmark_return
                        if stock_return is not None
                        and benchmark_return is not None
                        else None
                    )
                    beta, correlation = beta_and_correlation(
                        candles,
                        index,
                        benchmark_rows,
                        benchmark_index,
                        window,
                    )
                    relative[
                        f"beta_to_{benchmark.lower()}_{window}d"
                    ] = beta
                    relative[
                        f"correlation_to_{benchmark.lower()}_{window}d"
                    ] = correlation
            gross = pct_change(float(exit_row["close"]), float(entry["open"]))
            symbol_output.append(
                {
                    "symbol": symbol,
                    "market_date": market_date,
                    "market_session_index": calendar_index[market_date],
                    "decision_adjusted_close": float(decision["close"]),
                    **features,
                    **benchmark_cache[market_date],
                    **relative,
                    "label_entry_market_date": entry["market_date"],
                    "label_entry_next_adjusted_open": round(
                        float(entry["open"]), 8
                    ),
                    f"label_{horizon_sessions}d_exit_market_date": exit_row[
                        "market_date"
                    ],
                    f"label_{horizon_sessions}d_exit_adjusted_close": round(
                        float(exit_row["close"]), 8
                    ),
                    f"label_{horizon_sessions}d_gross_return_pct": round(
                        gross, 8
                    ),
                    f"label_{horizon_sessions}d_net_return_pct": round(
                        gross - ROUND_TRIP_COST_PCT, 8
                    ),
                    "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
                    "label_contract": (
                        "decision after completed close; enter next adjusted "
                        f"open; exit {horizon_sessions}th subsequent adjusted close"
                    ),
                    "research_only": True,
                    "execution_enabled": False,
                }
            )
        return symbol_output

    output: list[dict[str, Any]] = []
    if workers <= 1:
        symbol_groups = [build_symbol(symbol) for symbol in candidates]
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            symbol_groups = list(executor.map(build_symbol, candidates))
    for group in symbol_groups:
        output.extend(group)
    output.sort(key=lambda row: (row["market_date"], row["symbol"]))
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-root", type=Path, required=True)
    parser.add_argument("--candidates-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-date", default="2000-01-01")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--decision-stride", type=int, default=5)
    parser.add_argument(
        "--horizon-sessions",
        type=int,
        choices=(20, 60, 126),
        default=HORIZON_SESSIONS,
    )
    args = parser.parse_args()

    candidates = read_candidates(args.candidates_file)
    required = [*candidates, *BENCHMARKS]
    manifest_path = args.daily_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "complete"
        or manifest.get("failed")
        or manifest.get("function") != "TIME_SERIES_DAILY_ADJUSTED"
        or manifest.get("outputsize") != "full"
        or set(manifest.get("completed") or []) != set(required)
    ):
        raise ValueError("full adjusted-daily manifest does not match 101+2 universe")

    daily = {}
    hashes = {}
    for symbol in required:
        path = args.daily_root / f"{symbol}_daily.json"
        daily[symbol] = load_adjusted_daily(path)
        hashes[symbol] = sha256(path)
    if args.workers < 1 or args.workers > 16:
        raise ValueError("workers must be between 1 and 16")
    if args.decision_stride < 1 or args.decision_stride > 20:
        raise ValueError("decision stride must be between 1 and 20")
    rows = build_rows(
        daily,
        candidates,
        args.start_date,
        args.workers,
        args.decision_stride,
        args.horizon_sessions,
    )
    if not rows:
        raise ValueError("panel is empty")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    dates = sorted({row["market_date"] for row in rows})
    manifest_output = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "panel": str(args.output),
        "panel_sha256": sha256(args.output),
        "source_manifest": str(manifest_path),
        "source_manifest_sha256": sha256(manifest_path),
        "source": "Alpha Vantage TIME_SERIES_DAILY_ADJUSTED full",
        "candidate_universe": "fixed June 2026 Nasdaq-100 membership (101 securities)",
        "candidates": candidates,
        "candidate_count": len(candidates),
        "context_only_symbols": list(BENCHMARKS),
        "rows": len(rows),
        "dates": len(dates),
        "first_date": dates[0],
        "last_date": dates[-1],
        "horizon_sessions": args.horizon_sessions,
        "build_workers": args.workers,
        "decision_stride_market_sessions": args.decision_stride,
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        "raw_file_sha256": hashes,
        "warnings": [
            "fixed current-membership universe creates survivorship bias",
            "delisted historical constituents are not represented",
            "adjacent 126-session outcomes overlap and require embargo/HAC/non-overlap audits",
        ],
    }
    output_manifest = args.output.with_suffix(".manifest.json")
    output_manifest.write_text(
        json.dumps(manifest_output, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "output": str(args.output),
                "manifest": str(output_manifest),
                "rows": len(rows),
                "dates": len(dates),
                "first_date": dates[0],
                "last_date": dates[-1],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
