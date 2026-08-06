from __future__ import annotations

"""Build a point-in-time daily + five-minute cross-sectional research panel."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from alientai_v2.research.multiresolution_cross_sectional import (
    DAILY_FEATURES,
    FIVE_MINUTE_FEATURES,
    NEWS_FEATURES,
    OPTION_FEATURES,
    add_cross_sectional_ranks,
    add_option_history_features,
    five_minute_session_features,
    market_context_features,
    rank_target,
    requested_daily_features,
)
from build_nasdaq_qqq_spy_60session_panel import load_adjusted_daily


ROUND_TRIP_COST_PCT = 0.25
MIN_HISTORY = 60
MIN_DOLLAR_VOLUME = 20_000_000.0
HORIZONS = (5, 20)
CONTEXT_SYMBOLS = ("QQQ", "SPY")

DEFAULT_NASDAQ_DAILY = Path(
    r"D:\AlientAI\Data\AlphaVantage_2026"
    r"\nasdaq101_qqq_spy_daily_adjusted_full_20260806_preopen"
)
DEFAULT_NASDAQ_INTRADAY = Path(
    r"D:\AlientAI\Data\AlphaVantage_2026"
    r"\rolling_20m_nasdaq101_adjusted_1min_202001_202607"
)
DEFAULT_SP500_DAILY = Path("data_v2/sp500_daily_schwab_max_history")
DEFAULT_SP500_INTRADAY = Path(
    r"D:\AlientAI\Data\AlphaVantage_2026"
    r"\selective_natural_premarket_5min_2026"
)
DEFAULT_OPTIONS = Path(
    "data_v2/rcef_research/natural_option_features_2026.jsonl"
)
DEFAULT_NEWS = Path(
    r"D:\AlientAI\Data\Compiled\multiresolution_cross_sectional_20260806"
    r"\stratified_news_features_partial_15745.jsonl"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_symbols(path: Path) -> list[str]:
    symbols = [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not symbols or len(symbols) != len(set(symbols)):
        raise ValueError(f"invalid symbol file: {path}")
    return symbols


def read_sp500_daily(path: Path, symbol: str) -> list[dict[str, Any]]:
    vendor_symbol = symbol.replace(".", "-")
    source = path / f"{vendor_symbol}_schwab_1d_max.csv"
    frame = pd.read_csv(source)
    required = {"date", "open", "high", "low", "close", "volume"}
    if not required.issubset(frame.columns):
        raise ValueError(f"daily file missing columns: {source}")
    # Schwab's stored candle key is one calendar day before the U.S. session.
    frame["market_date"] = (
        pd.to_datetime(frame["date"], errors="raise") + pd.Timedelta(days=1)
    ).dt.strftime("%Y-%m-%d")
    frame = frame.sort_values("market_date")
    if frame["market_date"].duplicated().any():
        raise ValueError(f"duplicate mapped daily session: {source}")
    rows = []
    invalid_rows = 0
    for row in frame.itertuples(index=False):
        values = {
            "market_date": str(row.market_date),
            "open": float(row.open),
            "high": float(row.high),
            "low": float(row.low),
            "close": float(row.close),
            "volume": float(row.volume),
        }
        if min(values[name] for name in ("open", "high", "low", "close")) <= 0:
            # A few old Schwab split-adjusted histories contain impossible
            # pre-listing/legacy lows. Quarantine those individual rows; they
            # cannot enter a ratio feature and are years before this panel.
            invalid_rows += 1
            continue
        rows.append(values)
    if len(rows) < 100:
        raise ValueError(
            f"insufficient valid daily history after quarantining "
            f"{invalid_rows} rows: {source}"
        )
    return rows


def load_daily(
    universe: str,
    symbols: Iterable[str],
    *,
    nasdaq_root: Path,
    sp500_root: Path,
) -> dict[str, list[dict[str, Any]]]:
    output = {}
    for symbol in [*symbols, *CONTEXT_SYMBOLS]:
        if universe == "nasdaq100" or symbol in CONTEXT_SYMBOLS:
            output[symbol] = load_adjusted_daily(
                nasdaq_root / f"{symbol}_daily.json"
            )
        else:
            output[symbol] = read_sp500_daily(sp500_root, symbol)
    return output


def intraday_paths(root: Path, symbol: str) -> list[Path]:
    vendor_symbol = symbol.replace(".", "-")
    return sorted((root / "2026").glob(f"*/{vendor_symbol}.csv.gz"))


def load_intraday_features(
    root: Path,
    symbols: Iterable[str],
    *,
    source_interval_minutes: int,
    first_date: str,
    last_date: str,
) -> tuple[dict[tuple[str, str], dict[str, float]], dict[str, Any]]:
    output: dict[tuple[str, str], dict[str, float]] = {}
    files = 0
    raw_rows = 0
    for position, symbol in enumerate(symbols, start=1):
        for path in intraday_paths(root, symbol):
            files += 1
            frame = pd.read_csv(path, compression="gzip")
            if "timestamp" not in frame:
                raise ValueError(f"timestamp missing: {path}")
            frame["timestamp"] = pd.to_datetime(
                frame["timestamp"], errors="coerce"
            )
            frame = frame.dropna(subset=["timestamp"])
            dates = frame["timestamp"].dt.strftime("%Y-%m-%d")
            frame = frame[(dates >= first_date) & (dates <= last_date)].copy()
            raw_rows += len(frame)
            if frame.empty:
                continue
            frame["market_date"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
            for market_date, group in frame.groupby("market_date", sort=True):
                key = (symbol, str(market_date))
                if key in output:
                    raise ValueError(f"duplicate intraday session: {key}")
                features = five_minute_session_features(
                    group,
                    source_interval_minutes=source_interval_minutes,
                )
                if features is not None:
                    output[key] = features
        if position % 50 == 0:
            print(
                json.dumps(
                    {
                        "progress": "intraday",
                        "symbols_processed": position,
                        "symbols_total": len(list(symbols))
                        if not isinstance(symbols, list)
                        else len(symbols),
                        "valid_sessions": len(output),
                    }
                ),
                flush=True,
            )
    return output, {
        "files_read": files,
        "raw_rows_in_window": raw_rows,
        "valid_complete_sessions": len(output),
    }


def load_options(path: Path) -> pd.DataFrame:
    frame = pd.read_json(path, lines=True)
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    frame["market_date"] = frame["market_date"].astype(str)
    valid = (
        frame["option_available"].fillna(False).astype(bool)
        & frame["option_chain_available"].fillna(False).astype(bool)
        & (pd.to_numeric(frame["option_contract_count"], errors="coerce") > 0)
    )
    frame["option_available"] = valid.astype(float)
    frame["call_volume"] = pd.to_numeric(
        frame["option_call_volume"], errors="coerce"
    ).where(valid)
    frame["call_open_interest"] = pd.to_numeric(
        frame["option_call_open_interest"], errors="coerce"
    ).where(valid)
    frame["near_money_call_iv"] = pd.to_numeric(
        frame["option_near_money_call_iv"], errors="coerce"
    ).where(valid)
    frame = add_option_history_features(frame)
    keep = [
        "symbol",
        "market_date",
        "option_available",
        *OPTION_FEATURES,
    ]
    return frame[keep].drop_duplicates(["symbol", "market_date"])


def load_news(path: Path) -> pd.DataFrame:
    frame = pd.read_json(path, lines=True)
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    parsed = pd.to_datetime(frame["as_of_utc"], utc=True, errors="raise")
    # Every frozen request must have been available before the 20:00 ET cutoff.
    eastern = parsed.dt.tz_convert("America/New_York")
    if (eastern.dt.hour >= 20).any():
        raise ValueError("news request occurred at or after decision cutoff")
    frame["market_date"] = eastern.dt.strftime("%Y-%m-%d")
    frame["news_available"] = frame["news_available"].fillna(False).astype(float)
    keep = ["symbol", "market_date", "news_available", *NEWS_FEATURES]
    return frame[keep].drop_duplicates(["symbol", "market_date"])


def date_coverage(
    frame: pd.DataFrame, symbols: set[str], available_column: str
) -> dict[str, float]:
    subset = frame[frame["symbol"].isin(symbols)].copy()
    subset = subset[pd.to_numeric(subset[available_column], errors="coerce") > 0]
    counts = subset.groupby("market_date")["symbol"].nunique()
    return {str(date): int(count) / len(symbols) for date, count in counts.items()}


def build_base_rows(
    daily: Mapping[str, list[dict[str, Any]]],
    symbols: list[str],
    intraday: Mapping[tuple[str, str], Mapping[str, float]],
    options: pd.DataFrame,
    news: pd.DataFrame,
    *,
    minimum_option_coverage: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    symbol_set = set(symbols)
    option_coverage = date_coverage(options, symbol_set, "option_available")
    news_coverage = date_coverage(news, symbol_set, "news_available")
    eligible_dates = sorted(
        date
        for date, coverage in option_coverage.items()
        if coverage >= minimum_option_coverage
    )
    if not eligible_dates:
        raise ValueError("no dates pass the option coverage contract")

    qqq_positions = {
        str(row["market_date"]): index
        for index, row in enumerate(daily["QQQ"])
    }
    spy_positions = {
        str(row["market_date"]): index
        for index, row in enumerate(daily["SPY"])
    }
    calendar = sorted(set(qqq_positions) & set(spy_positions))
    calendar_index = {date: index for index, date in enumerate(calendar)}
    context = {}
    for date in eligible_dates:
        q_index = qqq_positions.get(date)
        s_index = spy_positions.get(date)
        if q_index is None or s_index is None or min(q_index, s_index) < 59:
            continue
        context[date] = market_context_features(
            daily["QQQ"][max(0, q_index + 1 - 90) : q_index + 1],
            daily["SPY"][max(0, s_index + 1 - 90) : s_index + 1],
        )

    options_map = options.set_index(["symbol", "market_date"]).to_dict("index")
    news_map = news.set_index(["symbol", "market_date"]).to_dict("index")
    rows = []
    drop_reasons: dict[str, int] = defaultdict(int)
    for symbol in symbols:
        candles = daily[symbol]
        positions = {
            str(row["market_date"]): index
            for index, row in enumerate(candles)
        }
        for date in eligible_dates:
            index = positions.get(date)
            official = calendar_index.get(date)
            if (
                index is None
                or official is None
                or date not in context
                or index < MIN_HISTORY - 1
                or official + max(HORIZONS) >= len(calendar)
            ):
                drop_reasons["daily_or_label_unavailable"] += 1
                continue
            intraday_row = intraday.get((symbol, date))
            if intraday_row is None:
                drop_reasons["incomplete_intraday_or_afterhours"] += 1
                continue
            qqq_5d = context[date]["context_qqq_return_5d_pct"]
            spy_5d = context[date]["context_spy_return_5d_pct"]
            features = requested_daily_features(
                candles[max(0, index + 1 - 90) : index + 1],
                qqq_return_5d_pct=qqq_5d,
                spy_return_5d_pct=spy_5d,
            )
            if float(features["average_dollar_volume_20d"]) < MIN_DOLLAR_VOLUME:
                drop_reasons["liquidity"] += 1
                continue
            option = options_map.get((symbol, date), {})
            headline = news_map.get((symbol, date), {})
            row: dict[str, Any] = {
                "symbol": symbol,
                "market_date": date,
                "decision_available_at_et": pd.Timestamp(
                    f"{date} 20:00:00", tz="America/New_York"
                ).isoformat(),
                **features,
                **intraday_row,
                **context[date],
                "option_available": float(option.get("option_available", 0.0)),
                "news_available": float(headline.get("news_available", 0.0)),
                "option_cross_sectional_coverage_fraction": option_coverage.get(
                    date, 0.0
                ),
                "news_cross_sectional_coverage_fraction": news_coverage.get(
                    date, 0.0
                ),
                "research_only": True,
                "execution_decision": "AVOID",
                "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
            }
            for name in OPTION_FEATURES:
                row[name] = option.get(name, np.nan)
            for name in NEWS_FEATURES:
                row[name] = headline.get(name, np.nan)
            for horizon in HORIZONS:
                entry_date = calendar[official + 1]
                exit_date = calendar[official + horizon]
                entry_index = positions.get(entry_date)
                exit_index = positions.get(exit_date)
                if entry_index is None or exit_index is None:
                    row = {}
                    drop_reasons[f"label_{horizon}d_missing_symbol_session"] += 1
                    break
                entry = float(candles[entry_index]["open"])
                exit_price = float(candles[exit_index]["close"])
                gross = (exit_price / entry - 1.0) * 100.0
                row[f"label_{horizon}d_entry_date"] = entry_date
                row[f"label_{horizon}d_exit_date"] = exit_date
                row[f"label_{horizon}d_gross_return_pct"] = gross
                row[f"label_{horizon}d_net_return_pct"] = (
                    gross - ROUND_TRIP_COST_PCT
                )
            if row:
                rows.append(row)

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("compiled panel is empty")
    rank_columns = [
        *DAILY_FEATURES,
        *FIVE_MINUTE_FEATURES,
        *OPTION_FEATURES,
        *NEWS_FEATURES,
    ]
    frame = add_cross_sectional_ranks(frame, rank_columns)
    for horizon in HORIZONS:
        frame[f"label_{horizon}d_cross_sectional_rank"] = rank_target(
            frame, f"label_{horizon}d_net_return_pct"
        )
    frame = frame.sort_values(["market_date", "symbol"]).reset_index(drop=True)
    return frame, {
        "eligible_option_dates": len(eligible_dates),
        "first_eligible_date": eligible_dates[0],
        "last_eligible_date": eligible_dates[-1],
        "option_coverage_by_date": option_coverage,
        "news_coverage_by_date": news_coverage,
        "drop_reasons": dict(drop_reasons),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--universe", choices=("nasdaq100", "sp500"), required=True
    )
    parser.add_argument("--symbols", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--nasdaq-daily-root", type=Path, default=DEFAULT_NASDAQ_DAILY)
    parser.add_argument(
        "--nasdaq-intraday-root", type=Path, default=DEFAULT_NASDAQ_INTRADAY
    )
    parser.add_argument("--sp500-daily-root", type=Path, default=DEFAULT_SP500_DAILY)
    parser.add_argument(
        "--sp500-intraday-root", type=Path, default=DEFAULT_SP500_INTRADAY
    )
    parser.add_argument("--options", type=Path, default=DEFAULT_OPTIONS)
    parser.add_argument("--news", type=Path, default=DEFAULT_NEWS)
    args = parser.parse_args()

    symbols = read_symbols(args.symbols)
    expected = 101 if args.universe == "nasdaq100" else 483
    if len(symbols) != expected or set(symbols) & set(CONTEXT_SYMBOLS):
        raise ValueError(f"expected {expected} candidates and context-only ETFs")
    daily = load_daily(
        args.universe,
        symbols,
        nasdaq_root=args.nasdaq_daily_root,
        sp500_root=args.sp500_daily_root,
    )
    intraday_root = (
        args.nasdaq_intraday_root
        if args.universe == "nasdaq100"
        else args.sp500_intraday_root
    )
    intraday, intraday_audit = load_intraday_features(
        intraday_root,
        symbols,
        source_interval_minutes=1 if args.universe == "nasdaq100" else 5,
        first_date="2026-01-02",
        last_date="2026-07-31",
    )
    options = load_options(args.options)
    news = load_news(args.news)
    frame, coverage = build_base_rows(
        daily,
        symbols,
        intraday,
        options,
        news,
        minimum_option_coverage=0.75
        if args.universe == "nasdaq100"
        else 0.90,
    )
    args.output_root.mkdir(parents=True, exist_ok=True)
    panel_path = args.output_root / "panel.csv.gz"
    frame.to_csv(panel_path, index=False, compression="gzip")
    manifest = {
        "status": "complete",
        "schema_version": 1,
        "model_family": "multiresolution_cross_sectional_ranker",
        "universe": args.universe,
        "candidate_count": len(symbols),
        "context_only": list(CONTEXT_SYMBOLS),
        "rows": len(frame),
        "dates": int(frame["market_date"].nunique()),
        "first_date": str(frame["market_date"].min()),
        "last_date": str(frame["market_date"].max()),
        "symbols_present": int(frame["symbol"].nunique()),
        "horizons_sessions": list(HORIZONS),
        "decision_cutoff_et": "20:00 after completed decision session",
        "entry": "next complete regular-session open",
        "exit": "fifth or twentieth subsequent regular-session close",
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        "minimum_average_dollar_volume_20d": MIN_DOLLAR_VOLUME,
        "source_contract": {
            "daily_candidates": "alpha_vantage_adjusted"
            if args.universe == "nasdaq100"
            else "schwab_max_history_mapped_plus_one_calendar_day",
            "daily_context_qqq_spy": "alpha_vantage_adjusted",
            "intraday": "alpha_vantage_1minute_aggregated_to_5minute"
            if args.universe == "nasdaq100"
            else "alpha_vantage_native_5minute",
            "options": "alpha_vantage_historical_option_chain_aggregate",
            "news": "alpha_vantage_news_sentiment_timestamp_filtered",
        },
        "fixed_contemporary_universe_bias": True,
        "call_purchase_limitation": (
            "aggregate call-side activity proxy; buyer initiation unavailable"
        ),
        "intraday_audit": intraday_audit,
        "coverage": coverage,
        "artifacts": {
            "symbols": {
                "path": str(args.symbols.resolve()),
                "sha256": sha256(args.symbols),
            },
            "options": {
                "path": str(args.options.resolve()),
                "sha256": sha256(args.options),
            },
            "news": {
                "path": str(args.news.resolve()),
                "sha256": sha256(args.news),
            },
            "panel": {
                "path": str(panel_path.resolve()),
                "sha256": sha256(panel_path),
            },
        },
        "research_only": True,
        "execution_decision": "AVOID",
    }
    manifest_path = args.output_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "universe": args.universe,
                "rows": len(frame),
                "dates": int(frame["market_date"].nunique()),
                "panel": str(panel_path),
                "manifest": str(manifest_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
