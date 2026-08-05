from __future__ import annotations

"""Build a long-history, point-in-time AI/semi five-session research panel.

The base panel is derived only from completed daily candles.  Optional catalyst
fields are joined by the exact symbol/market-date key and their missing history
remains explicitly unavailable.  Future labels from the overlay are never read.
"""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Iterable, Mapping

from alientai_v2.features.technical_snapshot import build_technical_snapshot


ROUND_TRIP_COST_PCT = 0.25
MIN_HISTORY = 60
TECHNICAL_WINDOW = 252
SAFE_OVERLAY_PREFIXES = (
    "model_premarket_",
    "narrative_news_",
    "narrative_earnings_",
    "narrative_fund_",
    "model_analyst_proxy_",
    "model_call_",
    "model_option_",
    "insider_",
    "short_interest_",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_universe(path: Path) -> list[str]:
    symbols = [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not symbols or len(symbols) != len(set(symbols)):
        raise ValueError("universe must contain unique symbols")
    return symbols


def load_daily(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    series = payload.get("Time Series (Daily)")
    if not isinstance(series, dict) or not series:
        raise ValueError(f"missing daily time series: {path}")
    rows = []
    for market_date, values in series.items():
        row = {
            "market_date": str(market_date),
            "open": float(values["1. open"]),
            "high": float(values["2. high"]),
            "low": float(values["3. low"]),
            "close": float(values["4. close"]),
            "volume": float(values["5. volume"]),
        }
        if min(row[name] for name in ("open", "high", "low", "close")) <= 0:
            raise ValueError(f"nonpositive daily price: {path.name}|{market_date}")
        rows.append(row)
    rows.sort(key=lambda row: row["market_date"])
    return rows


def read_overlay(path: Path | None) -> tuple[dict[tuple[str, str], dict[str, Any]], str | None]:
    if path is None:
        return {}, None
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            source = json.loads(line)
            key = (str(source["symbol"]).upper(), str(source["market_date"]))
            if key in rows:
                raise ValueError(f"duplicate catalyst overlay key: {key}")
            safe = {
                name: value
                for name, value in source.items()
                if name.startswith(SAFE_OVERLAY_PREFIXES)
            }
            if any(name.startswith("label_") for name in safe):
                raise ValueError("future label entered catalyst overlay")
            rows[key] = safe
    return rows, sha256(path)


def pct_change(current: float, prior: float) -> float:
    return (current / prior - 1.0) * 100.0


def lag_return(rows: list[dict[str, Any]], index: int, sessions: int) -> float | None:
    if index < sessions:
        return None
    return round(pct_change(rows[index]["close"], rows[index - sessions]["close"]), 6)


def cross_section_context(
    daily_by_symbol: Mapping[str, list[dict[str, Any]]],
) -> dict[str, dict[str, float]]:
    one_day: dict[str, list[float]] = defaultdict(list)
    five_day: dict[str, list[float]] = defaultdict(list)
    twenty_day: dict[str, list[float]] = defaultdict(list)
    for rows in daily_by_symbol.values():
        for index, row in enumerate(rows):
            market_date = row["market_date"]
            for sessions, target in (
                (1, one_day),
                (5, five_day),
                (20, twenty_day),
            ):
                value = lag_return(rows, index, sessions)
                if value is not None:
                    target[market_date].append(value)
    output: dict[str, dict[str, float]] = {}
    all_dates = set(one_day) | set(five_day) | set(twenty_day)
    for market_date in all_dates:
        day = one_day.get(market_date, [])
        output[market_date] = {
            "sector_ai17_mean_return_1d_pct": round(mean(day), 6) if day else 0.0,
            "sector_ai17_median_return_1d_pct": round(median(day), 6) if day else 0.0,
            "sector_ai17_fraction_positive_1d": (
                round(sum(value > 0.0 for value in day) / len(day), 6)
                if day else 0.0
            ),
            "sector_ai17_mean_return_5d_pct": (
                round(mean(five_day[market_date]), 6)
                if five_day.get(market_date) else 0.0
            ),
            "sector_ai17_mean_return_20d_pct": (
                round(mean(twenty_day[market_date]), 6)
                if twenty_day.get(market_date) else 0.0
            ),
            "sector_ai17_observed_symbols_1d": float(len(day)),
        }
    return output


def build_rows(
    daily_by_symbol: Mapping[str, list[dict[str, Any]]],
    overlay: Mapping[tuple[str, str], Mapping[str, Any]],
) -> Iterable[dict[str, Any]]:
    sector = cross_section_context(daily_by_symbol)
    for symbol in sorted(daily_by_symbol):
        candles = daily_by_symbol[symbol]
        for index in range(MIN_HISTORY - 1, len(candles) - 5):
            source = candles[index]
            entry = candles[index + 1]
            exit_row = candles[index + 5]
            start = max(0, index + 1 - TECHNICAL_WINDOW)
            technical = build_technical_snapshot(candles[start : index + 1])
            recent_returns = [
                pct_change(candles[offset]["close"], candles[offset - 1]["close"])
                for offset in range(max(1, index - 19), index + 1)
            ]
            gross = pct_change(exit_row["close"], entry["open"])
            catalyst = dict(overlay.get((symbol, source["market_date"]), {}))
            row = {
                "symbol": symbol,
                "market_date": source["market_date"],
                "close": source["close"],
                **technical,
                "return_5d_lag_pct": lag_return(candles, index, 5),
                "return_20d_lag_pct": lag_return(candles, index, 20),
                "return_60d_lag_pct": lag_return(candles, index, 60),
                "realized_volatility_20d_pct": (
                    round(pstdev(recent_returns), 6)
                    if len(recent_returns) >= 2 else None
                ),
                **sector.get(source["market_date"], {}),
                **catalyst,
                "catalyst_overlay_available": bool(catalyst),
                "label_entry_market_date": entry["market_date"],
                "label_entry_next_open": round(entry["open"], 6),
                "label_5d_exit_market_date": exit_row["market_date"],
                "label_5d_exit_close": round(exit_row["close"], 6),
                "label_5d_gross_return_pct": round(gross, 6),
                "label_5d_net_return_pct": round(
                    gross - ROUND_TRIP_COST_PCT, 6
                ),
                "label_5d_available": True,
                "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
                "label_contract": (
                    "decision after completed regular-session close; entry next "
                    "regular-session open; exit fifth subsequent session close"
                ),
                "research_only": True,
                "execution_enabled": False,
            }
            yield row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-root", type=Path, required=True)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--catalyst-overlay", type=Path)
    args = parser.parse_args()

    symbols = read_universe(args.universe)
    daily_by_symbol: dict[str, list[dict[str, Any]]] = {}
    source_hashes: dict[str, str] = {}
    for symbol in symbols:
        path = args.daily_root / f"{symbol}_daily.json"
        if not path.is_file():
            raise ValueError(f"missing daily source: {path}")
        daily_by_symbol[symbol] = load_daily(path)
        source_hashes[symbol] = sha256(path)
    overlay, overlay_hash = read_overlay(args.catalyst_overlay)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    first_date: str | None = None
    last_date: str | None = None
    overlay_count = 0
    with args.output.open("w", encoding="utf-8") as handle:
        for row in build_rows(daily_by_symbol, overlay):
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            count += 1
            overlay_count += int(row["catalyst_overlay_available"])
            date = str(row["market_date"])
            first_date = date if first_date is None or date < first_date else first_date
            last_date = date if last_date is None or date > last_date else last_date

    manifest = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "panel": str(args.output),
        "panel_sha256": sha256(args.output),
        "rows": count,
        "symbols": symbols,
        "universe_sha256": sha256(args.universe),
        "first_market_date": first_date,
        "last_market_date": last_date,
        "daily_root": str(args.daily_root),
        "daily_source_sha256": source_hashes,
        "catalyst_overlay": (
            str(args.catalyst_overlay) if args.catalyst_overlay else None
        ),
        "catalyst_overlay_sha256": overlay_hash,
        "rows_with_catalyst_overlay": overlay_count,
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        "technical_window_max_sessions": TECHNICAL_WINDOW,
        "point_in_time_contract": (
            "features use candles through market_date only; overlay uses exact "
            "symbol/date fields with all future labels excluded"
        ),
        "known_limitations": [
            "current thematic universe introduces survivorship and selection bias",
            "rich catalyst/premarket/options history is sparse before 2026",
            "daily bars cannot simulate intraday stop paths",
        ],
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"panel": str(args.output), "manifest": str(manifest_path),
                      "rows": count, "overlay_rows": overlay_count}, indent=2))


if __name__ == "__main__":
    main()
