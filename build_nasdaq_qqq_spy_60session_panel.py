from __future__ import annotations

"""Build a daily 60-session Nasdaq/QQQ/SPY research panel.

Alpha Vantage adjusted-daily rows are converted to split/dividend-adjusted
OHLCV before features or labels are calculated.  News and unusual-call fields
are optional exact-key overlays; unavailable history remains explicitly
missing and future labels are never copied from an overlay.
"""

import argparse
import hashlib
import json
from pathlib import Path
from statistics import pstdev
from typing import Any, Mapping, Sequence

from alientai_v2.features.technical_snapshot import build_technical_snapshot


HORIZON_SESSIONS = 60
ROUND_TRIP_COST_PCT = 0.25
MIN_HISTORY = 60
TECHNICAL_WINDOW = 252
CATALYST_PREFIXES = ("model_news_", "model_call_", "model_option_")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_symbols(path: Path) -> list[str]:
    values = [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(values) != 103 or len(values) != len(set(values)):
        raise ValueError("expected exactly 103 unique symbols")
    if not {"QQQ", "SPY"}.issubset(values):
        raise ValueError("QQQ and SPY are required")
    return values


def load_adjusted_daily(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    series = payload.get("Time Series (Daily)")
    if not isinstance(series, dict) or not series:
        raise ValueError(f"missing daily series: {path}")
    rows = []
    for market_date, values in series.items():
        raw_close = float(values["4. close"])
        adjusted_close = float(values.get("5. adjusted close", raw_close))
        if raw_close <= 0.0 or adjusted_close <= 0.0:
            raise ValueError(f"nonpositive close: {path.name}|{market_date}")
        factor = adjusted_close / raw_close
        raw_volume = float(values.get("6. volume", values.get("5. volume", 0.0)))
        row = {
            "market_date": str(market_date),
            "open": float(values["1. open"]) * factor,
            "high": float(values["2. high"]) * factor,
            "low": float(values["3. low"]) * factor,
            "close": adjusted_close,
            "volume": raw_volume / factor if factor > 0.0 else raw_volume,
            "adjustment_factor": factor,
        }
        if min(row[name] for name in ("open", "high", "low", "close")) <= 0:
            raise ValueError(f"nonpositive adjusted OHLC: {path.name}|{market_date}")
        rows.append(row)
    rows.sort(key=lambda row: row["market_date"])
    return rows


def read_overlay(path: Path | None) -> tuple[dict[tuple[str, str], dict[str, Any]], str | None]:
    if path is None:
        return {}, None
    output: dict[tuple[str, str], dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            source = json.loads(line)
            key = (str(source["symbol"]).upper(), str(source["market_date"]))
            if key in output:
                raise ValueError(f"duplicate catalyst key: {key}")
            output[key] = {
                name: value
                for name, value in source.items()
                if name.startswith(CATALYST_PREFIXES)
            }
            if any(name.startswith("label_") for name in output[key]):
                raise ValueError("future label entered catalyst overlay")
    return output, sha256(path)


def pct_change(current: float, prior: float) -> float:
    return (current / prior - 1.0) * 100.0


def lag_return(
    rows: Sequence[Mapping[str, Any]],
    index: int,
    sessions: int,
) -> float | None:
    if index < sessions:
        return None
    return round(
        pct_change(float(rows[index]["close"]), float(rows[index - sessions]["close"])),
        6,
    )


def benchmark_features(
    prefix: str,
    rows: Sequence[Mapping[str, Any]],
    index: int,
) -> dict[str, Any]:
    snapshot = build_technical_snapshot(
        rows[max(0, index + 1 - TECHNICAL_WINDOW) : index + 1]
    )
    return {
        **{
            name.replace("technical_", f"{prefix}_", 1): value
            for name, value in snapshot.items()
        },
        f"{prefix}_return_5d_pct": lag_return(rows, index, 5),
        f"{prefix}_return_20d_pct": lag_return(rows, index, 20),
        f"{prefix}_return_60d_pct": lag_return(rows, index, 60),
    }


def build_rows(
    daily: Mapping[str, list[dict[str, Any]]],
    symbols: Sequence[str],
    overlay: Mapping[tuple[str, str], Mapping[str, Any]],
    start_date: str,
) -> list[dict[str, Any]]:
    qqq_by_date = {
        row["market_date"]: (index, row)
        for index, row in enumerate(daily["QQQ"])
    }
    spy_by_date = {
        row["market_date"]: (index, row)
        for index, row in enumerate(daily["SPY"])
    }
    benchmark_cache: dict[str, dict[str, Any]] = {}
    for market_date in sorted(set(qqq_by_date) & set(spy_by_date)):
        qqq_index, _ = qqq_by_date[market_date]
        spy_index, _ = spy_by_date[market_date]
        if qqq_index < MIN_HISTORY - 1 or spy_index < MIN_HISTORY - 1:
            continue
        benchmark_cache[market_date] = {
            **benchmark_features("qqq", daily["QQQ"], qqq_index),
            **benchmark_features("spy", daily["SPY"], spy_index),
        }

    output = []
    for symbol in symbols:
        candles = daily[symbol]
        for index in range(MIN_HISTORY - 1, len(candles) - HORIZON_SESSIONS):
            source = candles[index]
            market_date = source["market_date"]
            if market_date < start_date or market_date not in benchmark_cache:
                continue
            entry = candles[index + 1]
            exit_row = candles[index + HORIZON_SESSIONS]
            technical = build_technical_snapshot(
                candles[max(0, index + 1 - TECHNICAL_WINDOW) : index + 1]
            )
            stock_returns = {
                sessions: lag_return(candles, index, sessions)
                for sessions in (5, 20, 60)
            }
            benchmarks = benchmark_cache[market_date]
            recent_returns = [
                pct_change(candles[offset]["close"], candles[offset - 1]["close"])
                for offset in range(max(1, index - 19), index + 1)
            ]
            catalyst = dict(overlay.get((symbol, market_date), {}))
            gross = pct_change(exit_row["close"], entry["open"])
            row = {
                "symbol": symbol,
                "market_date": market_date,
                "close": source["close"],
                **technical,
                "return_5d_lag_pct": stock_returns[5],
                "return_20d_lag_pct": stock_returns[20],
                "return_60d_lag_pct": stock_returns[60],
                "realized_volatility_20d_pct": (
                    round(pstdev(recent_returns), 6)
                    if len(recent_returns) >= 2 else None
                ),
                **benchmarks,
                **{
                    f"relative_to_qqq_{sessions}d_pct": (
                        round(
                            float(stock_returns[sessions])
                            - float(benchmarks[f"qqq_return_{sessions}d_pct"]),
                            6,
                        )
                        if stock_returns[sessions] is not None else None
                    )
                    for sessions in (5, 20, 60)
                },
                **{
                    f"relative_to_spy_{sessions}d_pct": (
                        round(
                            float(stock_returns[sessions])
                            - float(benchmarks[f"spy_return_{sessions}d_pct"]),
                            6,
                        )
                        if stock_returns[sessions] is not None else None
                    )
                    for sessions in (5, 20, 60)
                },
                **catalyst,
                "catalyst_overlay_available": bool(catalyst),
                "label_entry_market_date": entry["market_date"],
                "label_entry_next_open": round(entry["open"], 6),
                "label_60d_exit_market_date": exit_row["market_date"],
                "label_60d_exit_close": round(exit_row["close"], 6),
                "label_60d_gross_return_pct": round(gross, 6),
                "label_60d_net_return_pct": round(
                    gross - ROUND_TRIP_COST_PCT, 6
                ),
                "label_60d_available": True,
                "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
                "label_contract": (
                    "decision after completed regular-session close; enter next "
                    "session open; exit 60th subsequent session close"
                ),
                "research_only": True,
                "execution_enabled": False,
            }
            output.append(row)
    output.sort(key=lambda row: (row["market_date"], row["symbol"]))
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-root", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--catalyst-overlay", type=Path)
    parser.add_argument("--start-date", default="2020-01-01")
    args = parser.parse_args()

    symbols = read_symbols(args.symbols_file)
    manifest_path = args.daily_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "complete"
        or manifest.get("failed")
        or manifest.get("function") != "TIME_SERIES_DAILY_ADJUSTED"
        or manifest.get("outputsize") != "full"
    ):
        raise ValueError("adjusted full daily collection is not complete")
    if set(manifest.get("completed") or []) != set(symbols):
        raise ValueError("daily manifest does not match the exact universe")

    daily: dict[str, list[dict[str, Any]]] = {}
    hashes: dict[str, str] = {}
    for symbol in symbols:
        path = args.daily_root / f"{symbol}_daily.json"
        daily[symbol] = load_adjusted_daily(path)
        hashes[symbol] = sha256(path)
    overlay, overlay_hash = read_overlay(args.catalyst_overlay)
    rows = build_rows(daily, symbols, overlay, args.start_date)
    if not rows:
        raise ValueError("panel is empty")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    panel_manifest = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "panel": str(args.output),
        "panel_sha256": sha256(args.output),
        "rows": len(rows),
        "symbols": symbols,
        "symbols_sha256": sha256(args.symbols_file),
        "first_market_date": rows[0]["market_date"],
        "last_market_date": rows[-1]["market_date"],
        "horizon_sessions": HORIZON_SESSIONS,
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        "daily_source": "Alpha Vantage TIME_SERIES_DAILY_ADJUSTED full",
        "daily_source_manifest_sha256": sha256(manifest_path),
        "daily_source_hashes": hashes,
        "catalyst_overlay": (
            str(args.catalyst_overlay) if args.catalyst_overlay else None
        ),
        "catalyst_overlay_sha256": overlay_hash,
        "rows_with_catalyst_overlay": sum(
            bool(row["catalyst_overlay_available"]) for row in rows
        ),
        "point_in_time_contract": (
            "all price and benchmark features end on market_date; exact-key "
            "news/call overlay excludes every label/future field"
        ),
        "known_limitations": [
            "current 103-instrument universe is not point-in-time membership",
            "news and call-option history is much shorter than daily history",
            "60-session labels overlap heavily across adjacent decision dates",
        ],
    }
    output_manifest = args.output.with_suffix(".manifest.json")
    output_manifest.write_text(
        json.dumps(panel_manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "panel": str(args.output),
        "manifest": str(output_manifest),
        "rows": len(rows),
        "symbols": len(symbols),
        "overlay_rows": panel_manifest["rows_with_catalyst_overlay"],
    }, indent=2))


if __name__ == "__main__":
    main()
