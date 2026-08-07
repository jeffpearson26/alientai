from __future__ import annotations

"""Compile the frozen full-archive Nasdaq-101 daily/five-minute panel."""

import argparse
import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from alientai_v2.research.multiresolution_cross_sectional import (
    CONTEXT_FEATURES,
    DAILY_FEATURES,
    FIVE_MINUTE_FEATURES,
    add_cross_sectional_ranks,
    five_minute_session_features,
    market_context_features,
    rank_target,
    requested_daily_features,
)
from download_alpha_vantage_full_nasdaq_daily import series_filename, time_series
from download_alpha_vantage_full_nasdaq_5min import (
    month_range,
    series_relative_path,
)


MODEL_FAMILY = "full_archive_multiresolution_technical_ranker"
CONTEXT_SYMBOLS = ("QQQ", "SPY")
HORIZONS = (5, 20)
ROUND_TRIP_COST_PCT = 0.25
MIN_DOLLAR_VOLUME = 20_000_000.0
MIN_HISTORY = 60
MIN_PANEL_DATES = {5: 60, 20: 120}
MIN_COVERAGE_FRACTION = 0.95


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_symbols(path: Path) -> list[str]:
    symbols = [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if (
        len(symbols) != 101
        or len(symbols) != len(set(symbols))
        or set(symbols) & set(CONTEXT_SYMBOLS)
    ):
        raise ValueError("symbols must be exactly 101 unique non-context names")
    return symbols


def _adjusted_daily_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for market_date, values in time_series(dict(payload)).items():
        raw_close = float(values["4. close"])
        adjusted_close = float(values["5. adjusted close"])
        factor = adjusted_close / raw_close
        row = {
            "market_date": str(market_date),
            "open": float(values["1. open"]) * factor,
            "high": float(values["2. high"]) * factor,
            "low": float(values["3. low"]) * factor,
            "close": adjusted_close,
            # Raw volume is retained. Applying a later split factor to volume
            # can reveal a future corporate action.
            "volume": float(values["6. volume"]),
        }
        if (
            not all(math.isfinite(float(value)) for value in row.values() if not isinstance(value, str))
            or min(row[name] for name in ("open", "high", "low", "close")) <= 0
            or row["volume"] < 0
        ):
            raise ValueError(f"invalid adjusted-daily row: {market_date}")
        rows.append(row)
    rows.sort(key=lambda row: row["market_date"])
    if len(rows) < MIN_HISTORY:
        raise ValueError("daily series has insufficient history")
    return rows


def read_gzip_daily(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return _adjusted_daily_rows(json.load(handle))


def read_json_daily(path: Path) -> list[dict[str, Any]]:
    return _adjusted_daily_rows(json.loads(path.read_text(encoding="utf-8")))


def load_daily_sources(
    daily_archive: Path,
    spy_daily_file: Path,
    symbols: Sequence[str],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    manifest_path = daily_archive / "manifest.json"
    audit_path = daily_archive / "content_audit.json"
    spy_audit_path = spy_daily_file.parent / "content_audit.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    spy_audit = json.loads(spy_audit_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete" or not audit.get("integrity_pass"):
        raise ValueError("full daily archive has not passed its content audit")
    if spy_audit.get("status") != "PASS":
        raise ValueError("SPY daily source has not passed its content audit")
    completed = dict(manifest.get("completed") or {})
    output: dict[str, list[dict[str, Any]]] = {}
    for symbol in [*symbols, "QQQ"]:
        record = completed.get(symbol)
        if not record:
            raise ValueError(f"daily archive lacks completed {symbol}")
        expected = f"series/{series_filename(symbol)}"
        if str(record.get("path") or "") != expected:
            raise ValueError(f"daily path mismatch for {symbol}")
        output[symbol] = read_gzip_daily(daily_archive / expected)
    output["SPY"] = read_json_daily(spy_daily_file)
    return output, {
        "daily_manifest_path": str(manifest_path.resolve()),
        "daily_manifest_sha256": sha256(manifest_path),
        "daily_audit_path": str(audit_path.resolve()),
        "daily_audit_sha256": sha256(audit_path),
        "spy_daily_path": str(spy_daily_file.resolve()),
        "spy_daily_sha256": sha256(spy_daily_file),
        "spy_daily_audit_path": str(spy_audit_path.resolve()),
        "spy_daily_audit_sha256": sha256(spy_audit_path),
        "daily_adjustment": "same-date adjusted OHLC; raw volume",
    }


def intraday_paths(
    archive: Path,
    symbol: str,
    start_month: str,
    end_month: str,
) -> Iterable[Path]:
    for month in month_range(start_month, end_month):
        path = archive / "series" / series_relative_path(symbol, month)
        if path.exists():
            yield path


def load_intraday_features(
    archive: Path,
    symbols: Sequence[str],
    *,
    start_month: str,
    end_month: str,
) -> tuple[dict[tuple[str, str], dict[str, float]], dict[str, Any]]:
    contract_path = archive / "contract.json"
    audit_path = archive / "content_audit.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if (
        contract.get("interval") != "5min"
        or contract.get("adjusted") is not True
        or contract.get("extended_hours") is not True
        or not audit.get("integrity_pass")
    ):
        raise ValueError("five-minute archive contract/audit is not eligible")
    output: dict[tuple[str, str], dict[str, float]] = {}
    files = 0
    raw_rows = 0
    for position, symbol in enumerate(symbols, 1):
        for path in intraday_paths(
            archive,
            symbol,
            start_month,
            end_month,
        ):
            files += 1
            frame = pd.read_csv(path, compression="gzip")
            if not {
                "timestamp",
                "ticker",
                "open",
                "high",
                "low",
                "close",
                "volume",
            }.issubset(frame.columns):
                raise ValueError(f"normalized intraday columns missing: {path}")
            if set(frame["ticker"].astype(str)) != {symbol}:
                raise ValueError(f"intraday ticker mismatch: {path}")
            frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="raise")
            raw_rows += len(frame)
            frame["market_date"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
            for market_date, group in frame.groupby("market_date", sort=True):
                key = (symbol, str(market_date))
                if key in output:
                    raise ValueError(f"duplicate intraday session: {key}")
                features = five_minute_session_features(
                    group,
                    source_interval_minutes=5,
                )
                if features is not None:
                    output[key] = features
        if position % 20 == 0:
            print(
                json.dumps(
                    {
                        "progress": "intraday_features",
                        "symbols_processed": position,
                        "symbols_total": len(symbols),
                        "valid_sessions": len(output),
                    }
                ),
                flush=True,
            )
    return output, {
        "contract_path": str(contract_path.resolve()),
        "contract_sha256": sha256(contract_path),
        "audit_path": str(audit_path.resolve()),
        "audit_sha256": sha256(audit_path),
        "files_read": files,
        "raw_rows": raw_rows,
        "valid_sessions": len(output),
    }


def split_dates(dates: Sequence[str], horizon: int) -> dict[str, list[str]]:
    ordered = sorted(set(str(value) for value in dates))
    minimum = MIN_PANEL_DATES[horizon]
    if len(ordered) < minimum:
        raise ValueError(
            f"only {len(ordered)} dates; {minimum} required for {horizon}"
        )
    test_count = max(10, int(np.ceil(len(ordered) * 0.15)))
    test_start = len(ordered) - test_count
    embargo_start = max(0, test_start - horizon)
    development = ordered[:embargo_start]
    if len(development) < 30:
        raise ValueError("fewer than 30 development dates after test embargo")
    return {
        "development": development,
        "pre_test_embargo": ordered[embargo_start:test_start],
        "sealed_test": ordered[test_start:],
    }


def build_rows(
    daily: Mapping[str, list[dict[str, Any]]],
    symbols: Sequence[str],
    intraday: Mapping[tuple[str, str], Mapping[str, float]],
) -> tuple[pd.DataFrame, dict[str, int]]:
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
    for date in calendar:
        q_index = qqq_positions[date]
        s_index = spy_positions[date]
        if min(q_index, s_index) < MIN_HISTORY - 1:
            continue
        context[date] = market_context_features(
            daily["QQQ"][max(0, q_index + 1 - 90) : q_index + 1],
            daily["SPY"][max(0, s_index + 1 - 90) : s_index + 1],
        )
    rows: list[dict[str, Any]] = []
    dropped: dict[str, int] = defaultdict(int)
    intraday_dates: dict[str, list[str]] = defaultdict(list)
    for ticker, market_date in intraday:
        intraday_dates[ticker].append(market_date)
    for symbol in symbols:
        candles = daily[symbol]
        positions = {
            str(row["market_date"]): index
            for index, row in enumerate(candles)
        }
        dates = sorted(intraday_dates[symbol])
        for date in dates:
            index = positions.get(date)
            official = calendar_index.get(date)
            if (
                index is None
                or official is None
                or date not in context
                or index < MIN_HISTORY - 1
                or official + max(HORIZONS) >= len(calendar)
            ):
                dropped["daily_or_label_unavailable"] += 1
                continue
            features = requested_daily_features(
                candles[max(0, index + 1 - 90) : index + 1],
                qqq_return_5d_pct=context[date]["context_qqq_return_5d_pct"],
                spy_return_5d_pct=context[date]["context_spy_return_5d_pct"],
            )
            if float(features["average_dollar_volume_20d"]) < MIN_DOLLAR_VOLUME:
                dropped["liquidity"] += 1
                continue
            row: dict[str, Any] = {
                "symbol": symbol,
                "market_date": date,
                "decision_available_at_et": pd.Timestamp(
                    f"{date} 20:00:00",
                    tz="America/New_York",
                ).isoformat(),
                **features,
                **intraday[(symbol, date)],
                **context[date],
                "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
                "research_only": True,
                "execution_decision": "AVOID",
            }
            for horizon in HORIZONS:
                entry_date = calendar[official + 1]
                exit_date = calendar[official + horizon]
                entry_index = positions.get(entry_date)
                exit_index = positions.get(exit_date)
                if entry_index is None or exit_index is None:
                    row = {}
                    dropped[f"label_{horizon}_missing"] += 1
                    break
                entry = float(candles[entry_index]["open"])
                exit_price = float(candles[exit_index]["close"])
                gross = (exit_price / entry - 1.0) * 100.0
                row[f"label_{horizon}d_entry_date"] = entry_date
                row[f"label_{horizon}d_exit_date"] = exit_date
                row[f"label_{horizon}d_entry_open"] = entry
                row[f"label_{horizon}d_exit_close"] = exit_price
                row[f"label_{horizon}d_gross_return_pct"] = gross
                row[f"label_{horizon}d_net_return_pct"] = (
                    gross - ROUND_TRIP_COST_PCT
                )
            if row:
                rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("compiled panel is empty")
    minimum_symbols = int(math.ceil(len(symbols) * MIN_COVERAGE_FRACTION))
    counts = frame.groupby("market_date")["symbol"].nunique()
    keep_dates = set(counts[counts >= minimum_symbols].index.astype(str))
    frame = frame[frame["market_date"].astype(str).isin(keep_dates)].copy()
    if frame.empty:
        raise ValueError("no dates meet the cross-sectional coverage contract")
    frame = add_cross_sectional_ranks(
        frame,
        [*DAILY_FEATURES, *FIVE_MINUTE_FEATURES],
    )
    for horizon in HORIZONS:
        frame[f"label_{horizon}d_cross_sectional_rank"] = rank_target(
            frame,
            f"label_{horizon}d_net_return_pct",
        )
    frame = frame.sort_values(["market_date", "symbol"]).reset_index(drop=True)
    return frame, dict(dropped)


def write_csv(path: Path, frame: pd.DataFrame) -> dict[str, Any]:
    frame.to_csv(path, index=False, compression="gzip")
    return {
        "path": str(path.resolve()),
        "sha256": sha256(path),
        "rows": len(frame),
        "dates": int(frame["market_date"].nunique()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", type=Path, required=True)
    parser.add_argument("--daily-archive", type=Path, required=True)
    parser.add_argument("--intraday-archive", type=Path, required=True)
    parser.add_argument("--spy-daily-file", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--start-month", default="2016-08")
    parser.add_argument("--end-month", default="2026-07")
    args = parser.parse_args()
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise ValueError(f"output root must be new or empty: {args.output_root}")
    args.output_root.mkdir(parents=True, exist_ok=True)
    symbols = read_symbols(args.symbols)
    daily, daily_sources = load_daily_sources(
        args.daily_archive,
        args.spy_daily_file,
        symbols,
    )
    intraday, intraday_sources = load_intraday_features(
        args.intraday_archive,
        symbols,
        start_month=args.start_month,
        end_month=args.end_month,
    )
    frame, dropped = build_rows(daily, symbols, intraday)
    panel_artifact = write_csv(args.output_root / "panel.csv.gz", frame)
    partitions: dict[str, Any] = {}
    dates = sorted(frame["market_date"].astype(str).unique())
    for horizon in HORIZONS:
        split = split_dates(dates, horizon)
        development = frame[frame["market_date"].isin(split["development"])]
        test = frame[frame["market_date"].isin(split["sealed_test"])]
        partitions[str(horizon)] = {
            "split_dates": split,
            "development": write_csv(
                args.output_root / f"h{horizon:02d}_development.csv.gz",
                development,
            ),
            "sealed_test": write_csv(
                args.output_root / f"h{horizon:02d}_sealed_test.csv.gz",
                test,
            ),
        }
    manifest = {
        "schema_version": 1,
        "status": "complete",
        "model_family": MODEL_FAMILY,
        "model_ids": {
            "5": "full_archive_multiresolution_nasdaq101_h05_v1_20260807",
            "20": "full_archive_multiresolution_nasdaq101_h20_v1_20260807",
        },
        "universe": "nasdaq101",
        "candidate_count": len(symbols),
        "context_only": list(CONTEXT_SYMBOLS),
        "rows": len(frame),
        "dates": len(dates),
        "first_date": dates[0],
        "last_date": dates[-1],
        "horizons_sessions": list(HORIZONS),
        "decision_cutoff_et": "20:00 after completed decision session",
        "entry": "next complete regular-session open",
        "exit": "fifth or twentieth subsequent regular-session close",
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        "minimum_average_dollar_volume_20d": MIN_DOLLAR_VOLUME,
        "minimum_cross_sectional_coverage_fraction": MIN_COVERAGE_FRACTION,
        "feature_sets": ["daily_only", "daily_plus_5minute"],
        "excluded_families": [
            "options",
            "news",
            "fundamentals",
            "premarket",
        ],
        "daily_volume_policy": "raw point-in-time volume",
        "fixed_current_universe_survivorship_bias": True,
        "drop_reasons": dropped,
        "sources": {
            **daily_sources,
            "intraday": intraday_sources,
            "symbols_path": str(args.symbols.resolve()),
            "symbols_sha256": sha256(args.symbols),
        },
        "artifacts": {
            "panel": panel_artifact,
            "partitions": partitions,
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
                "rows": len(frame),
                "dates": len(dates),
                "first_date": dates[0],
                "last_date": dates[-1],
                "manifest": str(manifest_path),
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
