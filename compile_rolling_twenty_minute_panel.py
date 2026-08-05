from __future__ import annotations

"""Compile adjusted one-minute candles into executable intraday model shards."""

import argparse
import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from download_alpha_vantage_adjusted_intraday_archive import (
    atomic_json,
    month_range,
    read_symbols,
)


DEFAULT_HORIZON_MINUTES = 20
ALLOWED_HORIZON_MINUTES = (5, 10, 20, 30, 60, 90)
ROUND_TRIP_COST_PCT = 0.25
RETURN_WINDOWS = (1, 2, 5, 10, 20, 60)
ROLLING_WINDOWS = (5, 20, 60)
BENCHMARKS = ("QQQ", "SPY")
SCHEMA_VERSION = 3
TIMESTAMP_UNIT = "ns_since_unix_epoch"
ENTRY_ASSUMPTION = "next_minute_open"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_gzip_csv(path: Path) -> pd.DataFrame:
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        frame = pd.read_csv(handle)
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(frame.columns):
        raise ValueError(f"missing required columns in {path}")
    frame = frame[list(required)].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], format="%Y-%m-%d %H:%M:%S")
    for field in ("open", "high", "low", "close", "volume"):
        frame[field] = pd.to_numeric(frame[field], errors="raise")
    return frame.sort_values("timestamp").reset_index(drop=True)


def regular_minutes(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame[
        (frame["timestamp"].dt.time >= datetime.strptime("09:30", "%H:%M").time())
        & (frame["timestamp"].dt.time <= datetime.strptime("15:59", "%H:%M").time())
    ].copy()
    if output["timestamp"].duplicated().any():
        raise ValueError("duplicate one-minute timestamps")
    output["market_date"] = output["timestamp"].dt.strftime("%Y-%m-%d")
    output["minute_of_session"] = (
        output["timestamp"].dt.hour * 60
        + output["timestamp"].dt.minute
        - (9 * 60 + 30)
    )
    return output.reset_index(drop=True)


def _exact_lag(
    frame: pd.DataFrame,
    grouped: Any,
    field: str,
    minutes: int,
) -> tuple[pd.Series, pd.Series]:
    value = grouped[field].shift(minutes)
    stamp = grouped["timestamp"].shift(minutes)
    exact = (frame["timestamp"] - stamp) == pd.Timedelta(minutes=minutes)
    return value, exact.fillna(False)


def technical_frame(raw: pd.DataFrame) -> pd.DataFrame:
    frame = regular_minutes(raw)
    grouped = frame.groupby("market_date", sort=False, group_keys=False)
    first_open = grouped["open"].transform("first")
    cumulative_high = grouped["high"].cummax()
    cumulative_low = grouped["low"].cummin()
    cumulative_volume = grouped["volume"].cumsum()
    typical_value = (
        ((frame["high"] + frame["low"] + frame["close"]) / 3.0)
        * frame["volume"]
    )
    cumulative_typical_value = typical_value.groupby(frame["market_date"]).cumsum()

    frame["session_return_pct"] = (frame["close"] / first_open - 1.0) * 100.0
    frame["session_distance_from_high_pct"] = (
        frame["close"] / cumulative_high - 1.0
    ) * 100.0
    frame["session_distance_from_low_pct"] = (
        frame["close"] / cumulative_low - 1.0
    ) * 100.0
    vwap = cumulative_typical_value / cumulative_volume.replace(0, np.nan)
    frame["distance_from_session_vwap_pct"] = (frame["close"] / vwap - 1.0) * 100.0
    frame["minute_sin"] = np.sin(
        2.0 * np.pi * frame["minute_of_session"].astype(float) / 390.0
    )
    frame["minute_cos"] = np.cos(
        2.0 * np.pi * frame["minute_of_session"].astype(float) / 390.0
    )
    frame["day_of_week"] = frame["timestamp"].dt.dayofweek
    frame["candle_body_pct"] = (
        frame["close"] / frame["open"] - 1.0
    ) * 100.0
    frame["candle_range_pct"] = (
        frame["high"] / frame["low"] - 1.0
    ) * 100.0

    for window in RETURN_WINDOWS:
        lag, exact = _exact_lag(frame, grouped, "close", window)
        frame[f"history_{window}m_available"] = exact.astype(np.float32)
        frame[f"return_{window}m_pct"] = np.where(
            exact,
            (frame["close"] / lag - 1.0) * 100.0,
            np.nan,
        )

    one_minute_return = grouped["close"].pct_change(fill_method=None) * 100.0
    prior_stamp = grouped["timestamp"].shift(1)
    one_minute_return = one_minute_return.where(
        (frame["timestamp"] - prior_stamp) == pd.Timedelta(minutes=1)
    )
    realized_volatility = (
        one_minute_return.groupby(frame["market_date"])
        .rolling(20, min_periods=5)
        .std(ddof=0)
        .reset_index(level=0, drop=True)
    )
    volatility_start_stamp = grouped["timestamp"].shift(19)
    exact_volatility_history = (
        (frame["timestamp"] - volatility_start_stamp)
        == pd.Timedelta(minutes=19)
    )
    frame["realized_volatility_20m_pct"] = realized_volatility.where(
        exact_volatility_history
    )

    for window in ROLLING_WINDOWS:
        rolling_group = frame.groupby("market_date", sort=False)
        mean_volume = (
            rolling_group["volume"]
            .rolling(window, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
        )
        rolling_high = (
            rolling_group["high"]
            .rolling(window, min_periods=1)
            .max()
            .reset_index(level=0, drop=True)
        )
        rolling_low = (
            rolling_group["low"]
            .rolling(window, min_periods=1)
            .min()
            .reset_index(level=0, drop=True)
        )
        earliest_stamp = grouped["timestamp"].shift(window - 1)
        exact_history = (
            (frame["timestamp"] - earliest_stamp)
            == pd.Timedelta(minutes=window - 1)
        ).fillna(window == 1)
        frame[f"volume_history_{window}m_available"] = exact_history.astype(np.float32)
        frame[f"volume_vs_{window}m_mean"] = (
            frame["volume"] / mean_volume.replace(0, np.nan)
        ).where(
            exact_history
        )
        frame[f"range_{window}m_pct"] = (
            rolling_high / rolling_low - 1.0
        ).mul(100.0).where(exact_history)
    return frame


def feature_names() -> list[str]:
    names = [
        "minute_of_session",
        "minute_sin",
        "minute_cos",
        "day_of_week",
        "session_return_pct",
        "session_distance_from_high_pct",
        "session_distance_from_low_pct",
        "distance_from_session_vwap_pct",
        "candle_body_pct",
        "candle_range_pct",
        "realized_volatility_20m_pct",
    ]
    for window in RETURN_WINDOWS:
        names.extend([f"history_{window}m_available", f"return_{window}m_pct"])
    for window in ROLLING_WINDOWS:
        names.extend(
            [
                f"volume_history_{window}m_available",
                f"volume_vs_{window}m_mean",
                f"range_{window}m_pct",
            ]
        )
    for benchmark in BENCHMARKS:
        prefix = benchmark.lower()
        names.extend(
            [
                f"{prefix}_session_return_pct",
                f"{prefix}_realized_volatility_20m_pct",
            ]
        )
        names.extend(f"{prefix}_return_{window}m_pct" for window in RETURN_WINDOWS)
        names.extend(f"relative_to_{prefix}_{window}m_pct" for window in RETURN_WINDOWS)
    return names


def build_feature_frame(
    symbol_raw: pd.DataFrame,
    qqq_raw: pd.DataFrame,
    spy_raw: pd.DataFrame,
) -> pd.DataFrame:
    frame = technical_frame(symbol_raw)
    for benchmark, raw in (("qqq", qqq_raw), ("spy", spy_raw)):
        context = technical_frame(raw)
        keep = [
            "timestamp",
            "session_return_pct",
            "realized_volatility_20m_pct",
            *(f"return_{window}m_pct" for window in RETURN_WINDOWS),
        ]
        context = context[keep].rename(
            columns={
                name: f"{benchmark}_{name}"
                for name in keep
                if name != "timestamp"
            }
        )
        frame = frame.merge(context, on="timestamp", how="left", validate="one_to_one")
        for window in RETURN_WINDOWS:
            frame[f"relative_to_{benchmark}_{window}m_pct"] = (
                frame[f"return_{window}m_pct"]
                - frame[f"{benchmark}_return_{window}m_pct"]
            )

    return frame.reset_index(drop=True)


def build_training_frame(
    symbol_raw: pd.DataFrame,
    qqq_raw: pd.DataFrame,
    spy_raw: pd.DataFrame,
    *,
    horizon_minutes: int = DEFAULT_HORIZON_MINUTES,
    round_trip_cost_pct: float = ROUND_TRIP_COST_PCT,
) -> pd.DataFrame:
    if horizon_minutes not in ALLOWED_HORIZON_MINUTES:
        raise ValueError(
            f"horizon_minutes must be one of {ALLOWED_HORIZON_MINUTES}"
        )
    if round_trip_cost_pct < 0:
        raise ValueError("round_trip_cost_pct must be nonnegative")
    frame = build_feature_frame(symbol_raw, qqq_raw, spy_raw)
    grouped = frame.groupby("market_date", sort=False)
    entry_open = grouped["open"].shift(-1)
    entry_stamp = grouped["timestamp"].shift(-1)
    target_close = grouped["close"].shift(-horizon_minutes)
    target_bar_start_stamp = grouped["timestamp"].shift(-horizon_minutes)
    exact_entry = (
        entry_stamp - frame["timestamp"]
    ) == pd.Timedelta(minutes=1)
    exact_target = (
        target_bar_start_stamp - frame["timestamp"]
    ) == pd.Timedelta(minutes=horizon_minutes)
    frame["entry_timestamp"] = entry_stamp
    frame["target_bar_start_timestamp"] = target_bar_start_stamp
    frame["target_timestamp"] = (
        target_bar_start_stamp + pd.Timedelta(minutes=1)
    )
    frame["entry_open"] = entry_open
    frame["target_close"] = target_close
    frame["forward_return_gross_pct"] = (
        target_close / entry_open - 1.0
    ) * 100.0
    frame["forward_return_net_pct"] = (
        frame["forward_return_gross_pct"] - round_trip_cost_pct
    )
    frame["positive_after_cost"] = (
        frame["forward_return_net_pct"] > 0.0
    ).astype(np.float32)
    complete_context = frame[
        [
            "qqq_session_return_pct",
            "spy_session_return_pct",
        ]
    ].notna().all(axis=1)
    frame = frame[exact_entry & exact_target & complete_context].copy()
    return frame.reset_index(drop=True)


def save_shard(path: Path, frame: pd.DataFrame, names: list[str]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(
            handle,
            x=frame[names].to_numpy(dtype=np.float32),
            gross=frame["forward_return_gross_pct"].to_numpy(dtype=np.float32),
            net=frame["forward_return_net_pct"].to_numpy(dtype=np.float32),
            positive=frame["positive_after_cost"].to_numpy(dtype=np.float32),
            timestamp=frame["timestamp"]
            .to_numpy(dtype="datetime64[ns]")
            .astype(np.int64),
            entry_timestamp=frame["entry_timestamp"]
            .to_numpy(dtype="datetime64[ns]")
            .astype(np.int64),
            target_bar_start_timestamp=frame["target_bar_start_timestamp"]
            .to_numpy(dtype="datetime64[ns]")
            .astype(np.int64),
            target_timestamp=frame["target_timestamp"]
            .to_numpy(dtype="datetime64[ns]")
            .astype(np.int64),
        )
    os.replace(temporary, path)
    return {
        "rows": int(len(frame)),
        "output_bytes": path.stat().st_size,
        "output_sha256": file_sha256(path),
    }


def _records(manifest: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(item["symbol"]), str(item["month"])): item
        for item in manifest.get("completed") or []
    }


def compile_archive(
    raw_root: Path,
    output_root: Path,
    target_symbols: Iterable[str],
    allow_running_snapshot: bool = False,
    *,
    horizon_minutes: int = DEFAULT_HORIZON_MINUTES,
    round_trip_cost_pct: float = ROUND_TRIP_COST_PCT,
    supplemental_raw_roots: Iterable[Path] = (),
) -> dict[str, Any]:
    if horizon_minutes not in ALLOWED_HORIZON_MINUTES:
        raise ValueError(
            f"horizon_minutes must be one of {ALLOWED_HORIZON_MINUTES}"
        )
    if round_trip_cost_pct < 0:
        raise ValueError("round_trip_cost_pct must be nonnegative")
    requested_targets = sorted(set(target_symbols) - set(BENCHMARKS))
    if not requested_targets:
        raise ValueError("at least one non-benchmark target symbol is required")
    source_archives: list[tuple[Path, bytes, dict[str, Any]]] = []
    source_contract: dict[str, Any] | None = None
    for source_root in (raw_root, *tuple(supplemental_raw_roots)):
        manifest_path = source_root / "manifest.json"
        manifest_bytes = manifest_path.read_bytes()
        source_manifest = json.loads(manifest_bytes.decode("utf-8"))
        if source_manifest.get("failed"):
            raise ValueError(f"raw one-minute archive has failures: {source_root}")
        complete = source_manifest.get("status") == "complete"
        if not complete and not (
            allow_running_snapshot and source_manifest.get("status") == "running"
        ):
            raise ValueError(
                "raw one-minute archive must be complete with zero failures "
                "(or explicitly compiled as a running snapshot)"
            )
        if source_manifest.get("interval") != "1min":
            raise ValueError("raw archive is not one-minute data")
        archive_contract = {
            field: source_manifest.get(field)
            for field in (
                "start_month",
                "end_month",
                "function",
                "interval",
                "adjusted",
                "extended_hours",
                "timestamp_convention",
                "timestamp_timezone",
            )
        }
        if source_contract is None:
            source_contract = archive_contract
        elif archive_contract != source_contract:
            raise ValueError(
                f"source archive contract mismatch: {source_root}"
            )
        required_semantics = {
            "function": "TIME_SERIES_INTRADAY",
            "interval": "1min",
            "adjusted": True,
            "extended_hours": True,
            "timestamp_convention": "interval_start",
            "timestamp_timezone": "America/New_York",
        }
        if (
            not archive_contract["start_month"]
            or not archive_contract["end_month"]
            or any(
                archive_contract[field] != expected
                for field, expected in required_semantics.items()
            )
        ):
            raise ValueError(
                f"source archive has unsupported semantics: {source_root}"
            )
        source_archives.append(
            (source_root, manifest_bytes, source_manifest)
        )
    assert source_contract is not None
    source_complete = all(
        manifest.get("status") == "complete"
        for _, _, manifest in source_archives
    )
    records: dict[
        tuple[str, str],
        tuple[Path, dict[str, Any]],
    ] = {}
    targets = set(requested_targets)
    accounted_keys: set[tuple[str, str]] = set()
    for source_root, _, source_manifest in source_archives:
        accounted_keys.update(
            (str(record["symbol"]), str(record["month"]))
            for state in ("completed", "unavailable")
            for record in (source_manifest.get(state) or [])
            if str(record["symbol"]) in targets or str(record["symbol"]) in BENCHMARKS
        )
        for key, record in _records(source_manifest).items():
            symbol, _ = key
            if symbol not in targets and symbol not in BENCHMARKS:
                continue
            existing = records.get(key)
            if existing is None:
                records[key] = (source_root, record)
                continue
            if existing[1].get("content_sha256") != record.get("content_sha256"):
                raise ValueError(
                    f"conflicting duplicate source shard: {symbol}|{key[1]}"
                )
    expected_months = month_range(
        str(source_contract["start_month"]),
        str(source_contract["end_month"]),
    )
    if source_complete:
        missing_accounted = sorted(
            f"{symbol}|{month}"
            for symbol in (*requested_targets, *BENCHMARKS)
            for month in expected_months
            if (symbol, month) not in accounted_keys
        )
        if missing_accounted:
            preview = ", ".join(missing_accounted[:10])
            raise ValueError(
                "completed source archives do not account for every requested "
                f"symbol-month ({len(missing_accounted)} missing): {preview}"
            )
        targets_without_data = sorted(
            symbol
            for symbol in requested_targets
            if not any(key[0] == symbol for key in records)
        )
        if targets_without_data:
            raise ValueError(
                "target symbols have no usable completed data: "
                + ", ".join(targets_without_data)
            )
    names = feature_names()
    output_manifest_path = output_root / "manifest.json"
    contract: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "research_only": True,
        "execution_enabled": False,
        "partial_snapshot": not source_complete,
        "source_manifest_sha256": hashlib.sha256(
            source_archives[0][1]
        ).hexdigest(),
        "source_archives": [
            {
                "dataset": source_manifest.get("dataset"),
                "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            }
            for _, manifest_bytes, source_manifest in source_archives
        ],
        "source_interval": "1min",
        "source_start_month": source_contract["start_month"],
        "source_end_month": source_contract["end_month"],
        "timestamp_unit": TIMESTAMP_UNIT,
        "horizon_minutes": horizon_minutes,
        "round_trip_cost_pct": round_trip_cost_pct,
        "target_symbols": requested_targets,
        "target_symbols_count": len(requested_targets),
        "target_symbols_sha256": hashlib.sha256(
            ("\n".join(requested_targets) + "\n").encode("utf-8")
        ).hexdigest(),
        "entry_assumption": ENTRY_ASSUMPTION,
        "decision_timestamp_convention": "completed_bar_close",
        "entry_timestamp_convention": "next_interval_start",
        "target_timestamp_convention": "exit_bar_close",
        "feature_names": names,
    }
    if output_manifest_path.exists():
        output_manifest = json.loads(
            output_manifest_path.read_text(encoding="utf-8")
        )
        for field, expected in contract.items():
            if output_manifest.get(field) != expected:
                raise ValueError(f"compiled manifest contract mismatch: {field}")
    else:
        output_manifest = {
            **contract,
            "status": "running",
            "completed": [],
            "failed": [],
        }
    completed_by_key = {
        (str(item["symbol"]), str(item["month"])): item
        for item in output_manifest.get("completed") or []
    }
    by_month: dict[str, list[str]] = {}
    for symbol, month in records:
        if symbol in targets:
            by_month.setdefault(month, []).append(symbol)
    incomplete_context_months = sorted(
        month
        for month in by_month
        if any((benchmark, month) not in records for benchmark in BENCHMARKS)
    )
    if incomplete_context_months and source_complete:
        raise ValueError(
            "missing benchmark context for completed archive months: "
            + ", ".join(incomplete_context_months)
        )
    for month in incomplete_context_months:
        del by_month[month]
    if not by_month:
        raise ValueError("no source months have complete QQQ and SPY context")
    output_manifest["source_snapshot"] = {
        "source_status": "complete" if source_complete else "running_snapshot",
        "completed_requests": sum(
            len(manifest.get("completed") or [])
            for _, _, manifest in source_archives
        ),
        "unavailable_requests": sum(
            len(manifest.get("unavailable") or [])
            for _, _, manifest in source_archives
        ),
        "failed_requests": 0,
        "source_archive_count": len(source_archives),
        "compiled_months": sorted(by_month),
        "skipped_incomplete_context_months": incomplete_context_months,
    }
    try:
        for month in sorted(by_month):
            benchmark_frames = {}
            for benchmark in BENCHMARKS:
                source = records.get((benchmark, month))
                if source is None:
                    raise ValueError(f"missing {benchmark} context for {month}")
                source_root, record = source
                benchmark_frames[benchmark] = read_gzip_csv(
                    source_root / record["relative_path"]
                )
            for symbol in sorted(by_month[month]):
                source_root, record = records[(symbol, month)]
                existing = completed_by_key.get((symbol, month))
                if existing is not None:
                    existing_path = output_root / existing["relative_path"]
                    if (
                        existing.get("source_content_sha256")
                        == record["content_sha256"]
                        and existing_path.exists()
                        and existing.get("output_sha256") == file_sha256(existing_path)
                    ):
                        print(f"SKIP {symbol}|{month}", flush=True)
                        continue
                    raise ValueError(
                        f"existing compiled shard does not match source: {symbol}|{month}"
                    )
                frame = build_training_frame(
                    read_gzip_csv(source_root / record["relative_path"]),
                    benchmark_frames["QQQ"],
                    benchmark_frames["SPY"],
                    horizon_minutes=horizon_minutes,
                    round_trip_cost_pct=round_trip_cost_pct,
                )
                destination = (
                    output_root / month[:4] / month / f"{symbol}.npz"
                )
                metadata = save_shard(destination, frame, names)
                completed_by_key[(symbol, month)] = {
                    "symbol": symbol,
                    "month": month,
                    "source_content_sha256": record["content_sha256"],
                    "relative_path": destination.relative_to(output_root).as_posix(),
                    **metadata,
                }
                output_manifest["completed"] = list(completed_by_key.values())
                output_manifest["failed"] = []
                output_manifest["updated_at_utc"] = datetime.now(
                    timezone.utc
                ).isoformat()
                atomic_json(output_manifest_path, output_manifest)
                print(f"DONE {symbol}|{month}: {len(frame)} rows", flush=True)
    except Exception as exc:
        output_manifest["status"] = "failed_closed"
        output_manifest["failed"] = [{"error": str(exc)}]
        output_manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_json(output_manifest_path, output_manifest)
        raise
    output_manifest["status"] = "complete"
    output_manifest["completed"] = list(completed_by_key.values())
    output_manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    atomic_json(output_manifest_path, output_manifest)
    return output_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument(
        "--supplemental-raw-root",
        type=Path,
        action="append",
        default=[],
        help="Additional independently audited one-minute archive root",
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument(
        "--horizon-minutes",
        type=int,
        choices=ALLOWED_HORIZON_MINUTES,
        default=DEFAULT_HORIZON_MINUTES,
    )
    parser.add_argument(
        "--round-trip-cost-pct",
        type=float,
        default=ROUND_TRIP_COST_PCT,
    )
    parser.add_argument(
        "--allow-running-snapshot",
        action="store_true",
        help=(
            "Compile an immutable, explicitly partial pilot from the currently "
            "completed portion of a healthy running archive"
        ),
    )
    args = parser.parse_args()
    symbols = read_symbols(args.symbols_file)
    result = compile_archive(
        args.raw_root,
        args.output_root,
        symbols,
        allow_running_snapshot=args.allow_running_snapshot,
        horizon_minutes=args.horizon_minutes,
        round_trip_cost_pct=args.round_trip_cost_pct,
        supplemental_raw_roots=args.supplemental_raw_root,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "shards": len(result["completed"]),
                "rows": sum(item["rows"] for item in result["completed"]),
                "output": str(args.output_root.resolve()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
