from __future__ import annotations

"""Build the Nasdaq-101 plus AI/semi five-session technical panel."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from alientai_v2.research.cross_sectional_technical_5d import (
    add_date_local_ranks,
    eligibility,
    technical_features,
)
from build_nasdaq_qqq_spy_60session_panel import load_adjusted_daily, sha256


HORIZON_SESSIONS = 5
ROUND_TRIP_COST_PCT = 0.25
MIN_HISTORY = 60
CONTEXT = ("QQQ", "SPY")


def read_symbol_file(path: Path) -> list[str]:
    symbols = [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not symbols or len(symbols) != len(set(symbols)):
        raise ValueError(f"invalid symbol file: {path}")
    return symbols


def validate_manifest(
    root: Path, required: Sequence[str]
) -> tuple[Path, Mapping[str, Any]]:
    path = root / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    completed = set(manifest.get("completed") or [])
    if manifest.get("status") != "complete" or manifest.get("failed"):
        raise ValueError(f"incomplete source manifest: {path}")
    if (
        manifest.get("function") != "TIME_SERIES_DAILY_ADJUSTED"
        or manifest.get("outputsize") != "full"
    ):
        raise ValueError("archive is not full adjusted daily data")
    missing = set(required) - completed
    if missing:
        raise ValueError(f"source manifest missing symbols: {sorted(missing)}")
    return path, manifest


def market_context(
    candles: Sequence[Mapping[str, Any]], index: int, prefix: str
) -> dict[str, Any]:
    features = technical_features(candles[max(0, index + 1 - 90) : index + 1])
    keep = (
        "x5_return_1d_pct",
        "x5_return_5d_pct",
        "x5_return_10d_pct",
        "x5_realized_volatility_20d_annualized_pct",
        "x5_distance_ema_20_pct",
        "x5_adx_14",
    )
    return {
        f"market_{prefix}_{name.removeprefix('x5_')}": features[name]
        for name in keep
    }


def build_rows(
    daily: Mapping[str, list[dict[str, Any]]],
    candidates: Sequence[str],
    *,
    start_date: str,
    minimum_cross_sectional_coverage: float = 0.80,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    qqq_map = {
        str(row["market_date"]): index
        for index, row in enumerate(daily["QQQ"])
    }
    spy_map = {
        str(row["market_date"]): index
        for index, row in enumerate(daily["SPY"])
    }
    calendar = sorted(set(qqq_map) & set(spy_map))
    calendar_index = {value: index for index, value in enumerate(calendar)}
    context_cache = {}
    for market_date in calendar:
        q_index = qqq_map[market_date]
        s_index = spy_map[market_date]
        if min(q_index, s_index) < MIN_HISTORY - 1:
            continue
        context_cache[market_date] = {
            **market_context(daily["QQQ"], q_index, "qqq"),
            **market_context(daily["SPY"], s_index, "spy"),
        }

    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for symbol in candidates:
        candles = daily[symbol]
        positions = {
            str(row["market_date"]): index
            for index, row in enumerate(candles)
        }
        for market_date, index in positions.items():
            if market_date < start_date or market_date not in context_cache:
                continue
            official_index = calendar_index.get(market_date)
            if (
                official_index is None
                or official_index + HORIZON_SESSIONS >= len(calendar)
                or index < MIN_HISTORY - 1
            ):
                continue
            entry_date = calendar[official_index + 1]
            exit_date = calendar[official_index + HORIZON_SESSIONS]
            if entry_date not in positions or exit_date not in positions:
                continue
            entry_index = positions[entry_date]
            exit_index = positions[exit_date]
            if entry_index <= index or exit_index <= entry_index:
                continue
            features = technical_features(
                candles[max(0, index + 1 - 90) : index + 1]
            )
            eligible, failures = eligibility(features)
            entry_price = float(candles[entry_index]["open"])
            path = []
            for path_date in calendar[
                official_index + 1 : official_index + HORIZON_SESSIONS + 1
            ]:
                if path_date not in positions:
                    path = []
                    break
                close = float(candles[positions[path_date]]["close"])
                path.append(
                    {
                        "market_date": path_date,
                        "adjusted_close": round(close, 8),
                        "gross_return_from_entry_pct": round(
                            (close / entry_price - 1.0) * 100.0, 8
                        ),
                    }
                )
            if len(path) != HORIZON_SESSIONS:
                continue
            exit_price = float(candles[exit_index]["close"])
            gross = (exit_price / entry_price - 1.0) * 100.0
            by_date[market_date].append(
                {
                    "symbol": symbol,
                    "market_date": market_date,
                    "decision_adjusted_close": round(
                        float(candles[index]["close"]), 8
                    ),
                    **features,
                    **context_cache[market_date],
                    "x5_eligible": eligible,
                    "x5_eligibility_failures": failures,
                    "label_entry_market_date": entry_date,
                    "label_entry_next_adjusted_open": round(entry_price, 8),
                    "label_5d_exit_market_date": exit_date,
                    "label_5d_exit_adjusted_close": round(exit_price, 8),
                    "label_5d_gross_return_pct": round(gross, 8),
                    "label_5d_net_return_pct": round(
                        gross - ROUND_TRIP_COST_PCT, 8
                    ),
                    "label_5d_mark_to_market_path": path,
                    "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
                    "feature_available_at": f"{market_date} regular close",
                    "label_contract": (
                        "decision after completed close; enter next adjusted "
                        "regular open; exit fifth subsequent adjusted close"
                    ),
                    "research_only": True,
                    "execution_enabled": False,
                }
            )

    minimum_count = max(
        2, int(len(candidates) * minimum_cross_sectional_coverage + 0.999999)
    )
    rows = []
    dropped_dates = {}
    for market_date in sorted(by_date):
        group = by_date[market_date]
        if len(group) < minimum_count:
            dropped_dates[market_date] = len(group)
            continue
        for row in group:
            row["x5_cross_sectional_coverage_count"] = len(group)
            row["x5_cross_sectional_coverage_fraction"] = (
                len(group) / len(candidates)
            )
        rows.extend(group)
    add_date_local_ranks(rows)
    rows.sort(key=lambda row: (row["market_date"], row["symbol"]))
    return rows, {
        "minimum_cross_sectional_coverage_count": minimum_count,
        "dropped_dates_below_coverage": dropped_dates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-daily-root", type=Path, required=True)
    parser.add_argument("--ai-supplement-daily-root", type=Path, required=True)
    parser.add_argument("--nasdaq-symbols", type=Path, required=True)
    parser.add_argument("--ai-symbols", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-date", default="2020-01-01")
    parser.add_argument(
        "--minimum-cross-sectional-coverage", type=float, default=0.80
    )
    args = parser.parse_args()
    if not 0.50 <= args.minimum_cross_sectional_coverage <= 1.0:
        raise ValueError("coverage must be between 0.50 and 1.00")

    nasdaq = read_symbol_file(args.nasdaq_symbols)
    ai = read_symbol_file(args.ai_symbols)
    if len(nasdaq) != 101 or len(ai) != 17:
        raise ValueError("expected exact Nasdaq-101 and AI/semi-17 files")
    candidates = sorted(set(nasdaq) | set(ai))
    if len(candidates) != 104 or set(candidates) & set(CONTEXT):
        raise ValueError("expected 104 candidates with QQQ/SPY context only")

    primary_manifest, _ = validate_manifest(
        args.primary_daily_root, [*nasdaq, *CONTEXT]
    )
    supplement_extras = sorted(set(ai) - set(nasdaq))
    supplement_manifest, _ = validate_manifest(
        args.ai_supplement_daily_root, supplement_extras
    )
    daily = {}
    source_files = {}
    for symbol in [*candidates, *CONTEXT]:
        root = (
            args.primary_daily_root
            if symbol in set(nasdaq) | set(CONTEXT)
            else args.ai_supplement_daily_root
        )
        path = root / f"{symbol}_daily.json"
        daily[symbol] = load_adjusted_daily(path)
        source_files[symbol] = {
            "path": str(path),
            "sha256": sha256(path),
        }
    rows, coverage = build_rows(
        daily,
        candidates,
        start_date=args.start_date,
        minimum_cross_sectional_coverage=(
            args.minimum_cross_sectional_coverage
        ),
    )
    if not rows:
        raise ValueError("panel is empty")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    dates = sorted({str(row["market_date"]) for row in rows})
    report = {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "panel": str(args.output),
        "panel_sha256": sha256(args.output),
        "rows": len(rows),
        "dates": len(dates),
        "first_date": dates[0],
        "last_date": dates[-1],
        "candidate_count": len(candidates),
        "candidates": candidates,
        "nasdaq_count": len(nasdaq),
        "ai_screen_count": len(ai),
        "ai_additions_outside_nasdaq": supplement_extras,
        "context_only": list(CONTEXT),
        "horizon_sessions": HORIZON_SESSIONS,
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        "entry": "next regular-session adjusted open",
        "exit": "fifth subsequent regular-session adjusted close",
        "primary_manifest": str(primary_manifest),
        "primary_manifest_sha256": sha256(primary_manifest),
        "supplement_manifest": str(supplement_manifest),
        "supplement_manifest_sha256": sha256(supplement_manifest),
        "source_files": source_files,
        **coverage,
        "fixed_eligibility": {
            "minimum_price": 5.0,
            "minimum_average_dollar_volume_20d": 20_000_000.0,
            "maximum_atr_pct": 10.0,
            "minimum_adx": 15.0,
            "maximum_absolute_gap_pct": 10.0,
        },
        "warnings": [
            "fixed June/August 2026 universes create survivorship and selection bias",
            "ROC(10) and 10-session return are algebraically redundant in the supplied transparent formula",
            "upcoming earnings exclusion is not applied because complete point-in-time calendar history is unavailable",
        ],
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "panel": str(args.output),
                "manifest": str(manifest_path),
                "rows": len(rows),
                "dates": len(dates),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
