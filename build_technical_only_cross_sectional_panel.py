from __future__ import annotations

"""Build full-universe daily-technical-only cross-sectional panels."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from alientai_v2.research.multiresolution_cross_sectional import (
    CONTEXT_FEATURES,
    DAILY_FEATURES,
    add_cross_sectional_ranks,
    market_context_features,
    rank_target,
    requested_daily_features,
)
from build_multiresolution_cross_sectional_panel import (
    CONTEXT_SYMBOLS,
    DEFAULT_NASDAQ_DAILY,
    DEFAULT_SP500_DAILY,
    HORIZONS,
    MIN_DOLLAR_VOLUME,
    MIN_HISTORY,
    ROUND_TRIP_COST_PCT,
    load_daily,
    read_symbols,
    sha256,
)


def common_full_universe_dates(
    daily: Mapping[str, list[dict[str, Any]]],
    symbols: list[str],
) -> list[str]:
    common: set[str] | None = None
    for symbol in [*symbols, *CONTEXT_SYMBOLS]:
        dates = {str(row["market_date"]) for row in daily[symbol]}
        common = dates if common is None else common & dates
    if not common:
        raise ValueError("no full-universe daily overlap")
    return sorted(common)


def build_technical_rows(
    daily: Mapping[str, list[dict[str, Any]]],
    symbols: list[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    full_dates = common_full_universe_dates(daily, symbols)
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
    context: dict[str, dict[str, float]] = {}
    for date in full_dates:
        q_index = qqq_positions[date]
        s_index = spy_positions[date]
        official = calendar_index[date]
        if (
            min(q_index, s_index) < MIN_HISTORY - 1
            or official + max(HORIZONS) >= len(calendar)
        ):
            continue
        context[date] = market_context_features(
            daily["QQQ"][max(0, q_index + 1 - 90) : q_index + 1],
            daily["SPY"][max(0, s_index + 1 - 90) : s_index + 1],
        )
    eligible_dates = sorted(context)
    if len(eligible_dates) < 120:
        raise ValueError(
            f"only {len(eligible_dates)} dates remain after warm-up/labels"
        )

    rows_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    drop_reasons: dict[str, int] = defaultdict(int)
    for symbol in symbols:
        candles = daily[symbol]
        positions = {
            str(row["market_date"]): index
            for index, row in enumerate(candles)
        }
        for date in eligible_dates:
            index = positions[date]
            official = calendar_index[date]
            if index < MIN_HISTORY - 1:
                drop_reasons["symbol_warmup"] += 1
                continue
            reference = context[date]
            features = requested_daily_features(
                candles[max(0, index + 1 - 90) : index + 1],
                qqq_return_5d_pct=reference["context_qqq_return_5d_pct"],
                spy_return_5d_pct=reference["context_spy_return_5d_pct"],
            )
            if float(features["average_dollar_volume_20d"]) < MIN_DOLLAR_VOLUME:
                drop_reasons["liquidity"] += 1
                continue
            row: dict[str, Any] = {
                "symbol": symbol,
                "market_date": date,
                "decision_available_at_et": pd.Timestamp(
                    f"{date} 20:00:00", tz="America/New_York"
                ).isoformat(),
                **features,
                **reference,
                "research_only": True,
                "execution_decision": "AVOID",
                "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
            }
            for horizon in HORIZONS:
                entry_date = calendar[official + 1]
                exit_date = calendar[official + horizon]
                entry_index = positions.get(entry_date)
                exit_index = positions.get(exit_date)
                if entry_index is None or exit_index is None:
                    row = {}
                    drop_reasons[
                        f"label_{horizon}d_missing_symbol_session"
                    ] += 1
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
                rows_by_date[date].append(row)

    frame = pd.DataFrame(
        row
        for date in eligible_dates
        for row in rows_by_date.get(date, [])
        if len(rows_by_date.get(date, [])) == len(symbols)
    )
    dropped_incomplete_dates = {
        date: len(rows_by_date.get(date, []))
        for date in eligible_dates
        if len(rows_by_date.get(date, [])) != len(symbols)
    }
    if frame.empty:
        raise ValueError("technical-only panel is empty")
    if frame.groupby("market_date")["symbol"].nunique().min() != len(symbols):
        raise ValueError("full candidate coverage was not preserved")
    frame = add_cross_sectional_ranks(frame, DAILY_FEATURES)
    for horizon in HORIZONS:
        frame[f"label_{horizon}d_cross_sectional_rank"] = rank_target(
            frame, f"label_{horizon}d_net_return_pct"
        )
    frame = frame.sort_values(["market_date", "symbol"]).reset_index(drop=True)
    return frame, {
        "raw_full_universe_overlap_dates": len(full_dates),
        "eligible_after_warmup_and_labels": len(eligible_dates),
        "retained_complete_dates": int(frame["market_date"].nunique()),
        "first_retained_date": str(frame["market_date"].min()),
        "last_retained_date": str(frame["market_date"].max()),
        "dropped_incomplete_dates": dropped_incomplete_dates,
        "drop_reasons": dict(drop_reasons),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--universe", choices=("nasdaq100", "sp500"), required=True
    )
    parser.add_argument("--symbols", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--nasdaq-daily-root", type=Path, default=DEFAULT_NASDAQ_DAILY
    )
    parser.add_argument(
        "--sp500-daily-root", type=Path, default=DEFAULT_SP500_DAILY
    )
    args = parser.parse_args()
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise ValueError(f"output root must be new or empty: {args.output_root}")

    symbols = read_symbols(args.symbols)
    expected = 101 if args.universe == "nasdaq100" else 483
    if len(symbols) != expected or set(symbols) & set(CONTEXT_SYMBOLS):
        raise ValueError(f"expected {expected} candidates and QQQ/SPY context")
    daily = load_daily(
        args.universe,
        symbols,
        nasdaq_root=args.nasdaq_daily_root,
        sp500_root=args.sp500_daily_root,
    )
    frame, coverage = build_technical_rows(daily, symbols)
    args.output_root.mkdir(parents=True, exist_ok=True)
    panel_path = args.output_root / "panel.csv.gz"
    frame.to_csv(panel_path, index=False, compression="gzip")
    manifest = {
        "status": "complete",
        "schema_version": 1,
        "model_family": "technical_only_cross_sectional_ranker",
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
        "features": [*DAILY_FEATURES, *CONTEXT_FEATURES],
        "explicitly_excluded": [
            "options",
            "call_activity",
            "implied_volatility",
            "news",
            "headlines",
            "sentiment",
            "fundamentals",
            "earnings_events",
            "one_minute_candles",
            "five_minute_candles",
            "intraday",
            "premarket",
            "afterhours",
        ],
        "source_contract": {
            "candidate_candles": (
                "alpha_vantage_adjusted_daily"
                if args.universe == "nasdaq100"
                else "schwab_daily_max_history_mapped_plus_one_calendar_day"
            ),
            "context_qqq_spy": "alpha_vantage_adjusted_daily",
            "options": None,
            "intraday": None,
            "afterhours": None,
            "news": None,
            "fundamentals": None,
        },
        "full_candidate_coverage_required_each_date": True,
        "fixed_contemporary_universe_bias": True,
        "coverage": coverage,
        "artifacts": {
            "symbols": {
                "path": str(args.symbols.resolve()),
                "sha256": sha256(args.symbols),
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
