from __future__ import annotations

"""Compile adjusted one-minute candles into resumable 20-minute model shards."""

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
    read_symbols,
)


HORIZON_MINUTES = 20
ROUND_TRIP_COST_PCT = 0.25
RETURN_WINDOWS = (1, 2, 5, 10, 20, 60)
ROLLING_WINDOWS = (5, 20, 60)
BENCHMARKS = ("QQQ", "SPY")
SCHEMA_VERSION = 1


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
    frame["realized_volatility_20m_pct"] = (
        one_minute_return.groupby(frame["market_date"])
        .rolling(20, min_periods=5)
        .std(ddof=0)
        .reset_index(level=0, drop=True)
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
        frame[f"volume_vs_{window}m_mean"] = frame["volume"] / mean_volume.replace(
            0, np.nan
        )
        frame[f"range_{window}m_pct"] = (
            rolling_high / rolling_low - 1.0
        ) * 100.0
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


def build_training_frame(
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

    grouped = frame.groupby("market_date", sort=False)
    target_close = grouped["close"].shift(-HORIZON_MINUTES)
    target_stamp = grouped["timestamp"].shift(-HORIZON_MINUTES)
    exact_target = (
        target_stamp - frame["timestamp"]
    ) == pd.Timedelta(minutes=HORIZON_MINUTES)
    frame["target_timestamp"] = target_stamp
    frame["forward_return_20m_gross_pct"] = (
        target_close / frame["close"] - 1.0
    ) * 100.0
    frame["forward_return_20m_net_pct"] = (
        frame["forward_return_20m_gross_pct"] - ROUND_TRIP_COST_PCT
    )
    frame["positive_after_cost"] = (
        frame["forward_return_20m_net_pct"] > 0.0
    ).astype(np.float32)
    complete_context = frame[
        [
            "qqq_session_return_pct",
            "spy_session_return_pct",
        ]
    ].notna().all(axis=1)
    frame = frame[exact_target & complete_context].copy()
    return frame.reset_index(drop=True)


def save_shard(path: Path, frame: pd.DataFrame, names: list[str]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(
            handle,
            x=frame[names].to_numpy(dtype=np.float32),
            gross=frame["forward_return_20m_gross_pct"].to_numpy(dtype=np.float32),
            net=frame["forward_return_20m_net_pct"].to_numpy(dtype=np.float32),
            positive=frame["positive_after_cost"].to_numpy(dtype=np.float32),
            timestamp=frame["timestamp"].astype("int64").to_numpy(dtype=np.int64),
            target_timestamp=frame["target_timestamp"].astype("int64").to_numpy(
                dtype=np.int64
            ),
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
) -> dict[str, Any]:
    raw_manifest_path = raw_root / "manifest.json"
    raw_manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
    if raw_manifest.get("status") != "complete" or raw_manifest.get("failed"):
        raise ValueError("raw one-minute archive must be complete with zero failures")
    if raw_manifest.get("interval") != "1min":
        raise ValueError("raw archive is not one-minute data")
    records = _records(raw_manifest)
    names = feature_names()
    output_manifest_path = output_root / "manifest.json"
    contract: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "research_only": True,
        "execution_enabled": False,
        "source_manifest_sha256": file_sha256(raw_manifest_path),
        "source_interval": "1min",
        "horizon_minutes": HORIZON_MINUTES,
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
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
    targets = set(target_symbols) - set(BENCHMARKS)
    for symbol, month in records:
        if symbol in targets:
            by_month.setdefault(month, []).append(symbol)
    try:
        for month in sorted(by_month):
            benchmark_frames = {}
            for benchmark in BENCHMARKS:
                record = records.get((benchmark, month))
                if record is None:
                    raise ValueError(f"missing {benchmark} context for {month}")
                benchmark_frames[benchmark] = read_gzip_csv(
                    raw_root / record["relative_path"]
                )
            for symbol in sorted(by_month[month]):
                record = records[(symbol, month)]
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
                    read_gzip_csv(raw_root / record["relative_path"]),
                    benchmark_frames["QQQ"],
                    benchmark_frames["SPY"],
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
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    args = parser.parse_args()
    symbols = read_symbols(args.symbols_file)
    result = compile_archive(args.raw_root, args.output_root, symbols)
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
