from __future__ import annotations

"""Build the daily-candle-only technical and call-option research panel."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from alientai_v2.research.multiresolution_cross_sectional import (
    CONTEXT_FEATURES,
    DAILY_FEATURES,
    OPTION_FEATURES,
    add_cross_sectional_ranks,
    market_context_features,
    rank_target,
    requested_daily_features,
)
from build_multiresolution_cross_sectional_panel import (
    CONTEXT_SYMBOLS,
    DEFAULT_NASDAQ_DAILY,
    DEFAULT_OPTIONS,
    DEFAULT_SP500_DAILY,
    HORIZONS,
    MIN_DOLLAR_VOLUME,
    MIN_HISTORY,
    ROUND_TRIP_COST_PCT,
    date_coverage,
    load_daily,
    load_options,
    read_symbols,
    sha256,
)


def build_daily_rows(
    daily: Mapping[str, list[dict[str, Any]]],
    symbols: list[str],
    options: pd.DataFrame,
    *,
    minimum_option_coverage: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build rows without consulting an intraday, after-hours, or news source."""
    symbol_set = set(symbols)
    option_coverage = date_coverage(options, symbol_set, "option_available")
    eligible_dates = sorted(
        date
        for date, coverage in option_coverage.items()
        if coverage >= minimum_option_coverage
    )
    if not eligible_dates:
        raise ValueError("no dates pass the frozen option coverage contract")

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
    rows: list[dict[str, Any]] = []
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
            row: dict[str, Any] = {
                "symbol": symbol,
                "market_date": date,
                "decision_available_at_et": pd.Timestamp(
                    f"{date} 20:00:00", tz="America/New_York"
                ).isoformat(),
                **features,
                **context[date],
                "option_available": float(option.get("option_available", 0.0)),
                "option_cross_sectional_coverage_fraction": option_coverage.get(
                    date, 0.0
                ),
                "research_only": True,
                "execution_decision": "AVOID",
                "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
            }
            for name in OPTION_FEATURES:
                row[name] = option.get(name, np.nan)
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
                rows.append(row)

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("compiled daily-only panel is empty")
    frame = add_cross_sectional_ranks(
        frame, [*DAILY_FEATURES, *OPTION_FEATURES]
    )
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
    parser.add_argument("--options", type=Path, default=DEFAULT_OPTIONS)
    args = parser.parse_args()

    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise ValueError(f"output root must be new or empty: {args.output_root}")
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
    options = load_options(args.options)
    frame, coverage = build_daily_rows(
        daily,
        symbols,
        options,
        minimum_option_coverage=(
            0.75 if args.universe == "nasdaq100" else 0.90
        ),
    )

    args.output_root.mkdir(parents=True, exist_ok=True)
    panel_path = args.output_root / "panel.csv.gz"
    frame.to_csv(panel_path, index=False, compression="gzip")
    manifest = {
        "status": "complete",
        "schema_version": 1,
        "model_family": "daily_options_cross_sectional_ranker",
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
        "feature_sets": {
            "daily_technical": [*DAILY_FEATURES, *CONTEXT_FEATURES],
            "daily_technical_options": [
                *DAILY_FEATURES,
                *OPTION_FEATURES,
                "option_available",
                *CONTEXT_FEATURES,
            ],
        },
        "explicitly_excluded": [
            "one_minute_candles",
            "five_minute_candles",
            "intraday_features",
            "premarket_features",
            "afterhours_features",
            "news_features",
        ],
        "source_contract": {
            "candidate_candles": (
                "alpha_vantage_adjusted_daily"
                if args.universe == "nasdaq100"
                else "schwab_daily_max_history_mapped_plus_one_calendar_day"
            ),
            "context_qqq_spy": "alpha_vantage_adjusted_daily",
            "options": "alpha_vantage_historical_option_chain_aggregate",
            "intraday": None,
            "afterhours": None,
            "news": None,
        },
        "fixed_contemporary_universe_bias": True,
        "call_purchase_limitation": (
            "aggregate call-side activity proxy; buyer initiation unavailable"
        ),
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
