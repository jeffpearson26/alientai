from __future__ import annotations

"""Build matched AMD/NVDA five-session panels from 1m and 5m candles.

The prediction is made after a completed regular session.  Intraday features
use bars through that close only.  Entry is the next regular-session open and
exit is the fifth subsequent regular-session close.  Historical call activity
is attached only when an exact, non-empty Alpha Vantage chain exists.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from alientai_v2.features.option_chain_features import option_chain_features
from alientai_v2.research.historical_call_evaluator import load_chain
from alientai_v2.research.unusual_call_activity import unusual_call_features


SYMBOLS = ("AMD", "NVDA")
RESOLUTIONS = ("1min", "5min")
ROUND_TRIP_COST_PCT = 0.25
MIN_DAILY_HISTORY = 60


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_symbol(root: Path, symbol: str) -> pd.DataFrame:
    paths = sorted(root.glob(f"*/*/{symbol}.csv.gz"))
    if not paths:
        raise ValueError(f"no one-minute files found for {symbol}")
    frames = []
    for path in paths:
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
            frame = pd.read_csv(handle)
        required = ["timestamp", "open", "high", "low", "close", "volume"]
        if not set(required).issubset(frame.columns):
            raise ValueError(f"malformed candle file: {path}")
        frame = frame[required].copy()
        frame["timestamp"] = pd.to_datetime(
            frame["timestamp"], format="%Y-%m-%d %H:%M:%S"
        )
        frames.append(frame)
    output = pd.concat(frames, ignore_index=True)
    for name in ("open", "high", "low", "close", "volume"):
        output[name] = pd.to_numeric(output[name], errors="raise")
    output = output[
        (output["timestamp"].dt.time >= pd.Timestamp("09:30").time())
        & (output["timestamp"].dt.time <= pd.Timestamp("15:59").time())
    ].copy()
    output = output.sort_values("timestamp")
    if output.empty or output["timestamp"].duplicated().any():
        raise ValueError(f"invalid regular-session data for {symbol}")
    output["market_date"] = output["timestamp"].dt.strftime("%Y-%m-%d")
    output["symbol"] = symbol
    return output.reset_index(drop=True)


def resample_regular(frame: pd.DataFrame, resolution: str) -> pd.DataFrame:
    if resolution == "1min":
        return frame.copy()
    if resolution != "5min":
        raise ValueError(f"unsupported resolution: {resolution}")
    indexed = frame.set_index("timestamp")
    pieces = []
    for market_date, day in indexed.groupby("market_date", sort=True):
        bars = day.resample(
            "5min", origin="start_day", offset="30min", label="left", closed="left"
        ).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        bars = bars.dropna(subset=["open", "high", "low", "close"])
        bars["market_date"] = market_date
        bars["symbol"] = str(day["symbol"].iloc[0])
        pieces.append(bars.reset_index())
    return pd.concat(pieces, ignore_index=True)


def pct(current: float, prior: float) -> float:
    return (current / prior - 1.0) * 100.0


def slope_pct(values: np.ndarray) -> float | None:
    if len(values) < 2 or np.any(values <= 0):
        return None
    x = np.arange(len(values), dtype=float)
    slope = np.polyfit(x, np.log(values.astype(float)), 1)[0]
    return float((np.exp(slope) - 1.0) * 100.0)


def trailing_return(day: pd.DataFrame, minutes: int, resolution: str) -> float | None:
    step = 1 if resolution == "1min" else 5
    bars = minutes // step
    if bars < 1 or len(day) <= bars:
        return None
    return pct(float(day["close"].iloc[-1]), float(day["close"].iloc[-1 - bars]))


def session_features(day: pd.DataFrame, resolution: str) -> dict[str, Any]:
    day = day.sort_values("timestamp")
    close = day["close"].to_numpy(dtype=float)
    high = day["high"].to_numpy(dtype=float)
    low = day["low"].to_numpy(dtype=float)
    volume = day["volume"].to_numpy(dtype=float)
    typical = (
        day["high"].to_numpy(dtype=float)
        + day["low"].to_numpy(dtype=float)
        + close
    ) / 3.0
    total_volume = float(volume.sum())
    vwap = float(np.dot(typical, volume) / total_volume) if total_volume > 0 else np.nan
    returns = np.diff(np.log(close)) * 100.0
    running_peak = np.maximum.accumulate(close)
    drawdowns = close / running_peak - 1.0
    step = 1 if resolution == "1min" else 5
    last_30_bars = max(1, 30 // step)
    opening_30_bars = max(1, 30 // step)
    return {
        f"{resolution}_session_return_pct": pct(float(close[-1]), float(day["open"].iloc[0])),
        f"{resolution}_opening_30m_return_pct": pct(
            float(close[min(opening_30_bars - 1, len(close) - 1)]),
            float(day["open"].iloc[0]),
        ),
        f"{resolution}_return_5m_pct": trailing_return(day, 5, resolution),
        f"{resolution}_return_20m_pct": trailing_return(day, 20, resolution),
        f"{resolution}_return_60m_pct": trailing_return(day, 60, resolution),
        f"{resolution}_return_120m_pct": trailing_return(day, 120, resolution),
        f"{resolution}_realized_volatility_pct": (
            float(np.std(returns, ddof=0)) if len(returns) else None
        ),
        f"{resolution}_last_60m_volatility_pct": (
            float(np.std(returns[-max(1, 60 // step) :], ddof=0))
            if len(returns) else None
        ),
        f"{resolution}_session_range_pct": pct(float(high.max()), float(low.min())),
        f"{resolution}_close_location": (
            float((close[-1] - low.min()) / (high.max() - low.min()))
            if high.max() > low.min() else 0.5
        ),
        f"{resolution}_distance_from_vwap_pct": (
            pct(float(close[-1]), vwap) if np.isfinite(vwap) and vwap > 0 else None
        ),
        f"{resolution}_last_30m_volume_share": (
            float(volume[-last_30_bars:].sum() / total_volume)
            if total_volume > 0 else None
        ),
        f"{resolution}_log_price_slope_per_bar_pct": slope_pct(close),
        f"{resolution}_max_intraday_drawdown_pct": float(drawdowns.min() * 100.0),
        f"{resolution}_bar_count": float(len(day)),
    }


def make_daily(frame: pd.DataFrame, resolution: str) -> list[dict[str, Any]]:
    rows = []
    for market_date, day in frame.groupby("market_date", sort=True):
        day = day.sort_values("timestamp")
        first_time = day["timestamp"].iloc[0].time()
        last_time = day["timestamp"].iloc[-1].time()
        minimum_bars = 200 if resolution == "1min" else 40
        valid_last_times = (
            {pd.Timestamp("12:59").time(), pd.Timestamp("15:59").time()}
            if resolution == "1min"
            else {pd.Timestamp("12:55").time(), pd.Timestamp("15:55").time()}
        )
        if (
            first_time != pd.Timestamp("09:30").time()
            or last_time not in valid_last_times
            or len(day) < minimum_bars
        ):
            continue
        row = {
            "market_date": str(market_date),
            "open": float(day["open"].iloc[0]),
            "high": float(day["high"].max()),
            "low": float(day["low"].min()),
            "close": float(day["close"].iloc[-1]),
            "volume": float(day["volume"].sum()),
            **session_features(day, resolution),
        }
        rows.append(row)
    return rows


def lag_pct(rows: list[dict[str, Any]], index: int, sessions: int) -> float | None:
    if index < sessions:
        return None
    return pct(float(rows[index]["close"]), float(rows[index - sessions]["close"]))


def build_candle_rows(
    daily_by_symbol: dict[str, list[dict[str, Any]]],
    resolution: str,
) -> list[dict[str, Any]]:
    output = []
    for symbol, rows in sorted(daily_by_symbol.items()):
        for index in range(MIN_DAILY_HISTORY, len(rows) - 5):
            current, entry, exit_row = rows[index], rows[index + 1], rows[index + 5]
            recent_returns = [
                pct(float(rows[pos]["close"]), float(rows[pos - 1]["close"]))
                for pos in range(index - 19, index + 1)
            ]
            recent_high = max(float(row["high"]) for row in rows[index - 19 : index + 1])
            recent_volume = np.asarray(
                [float(row["volume"]) for row in rows[index - 19 : index + 1]]
            )
            gross = pct(float(exit_row["close"]), float(entry["open"]))
            output.append(
                {
                    "symbol": symbol,
                    "symbol_is_nvda": float(symbol == "NVDA"),
                    "market_date": current["market_date"],
                    "close": current["close"],
                    **{
                        key: value
                        for key, value in current.items()
                        if key.startswith(f"{resolution}_")
                    },
                    "daily_return_1d_pct": lag_pct(rows, index, 1),
                    "daily_return_5d_pct": lag_pct(rows, index, 5),
                    "daily_return_20d_pct": lag_pct(rows, index, 20),
                    "daily_return_60d_pct": lag_pct(rows, index, 60),
                    "daily_realized_volatility_20d_pct": float(
                        np.std(recent_returns, ddof=0)
                    ),
                    "daily_pullback_from_20d_high_pct": pct(
                        float(current["close"]), recent_high
                    ),
                    "daily_volume_vs_20d_mean": (
                        float(current["volume"]) / float(recent_volume.mean())
                        if recent_volume.mean() > 0 else None
                    ),
                    "label_entry_market_date": entry["market_date"],
                    "label_5d_exit_market_date": exit_row["market_date"],
                    "label_5d_gross_return_pct": gross,
                    "label_5d_net_return_pct": gross - ROUND_TRIP_COST_PCT,
                    "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
                    "label_contract": (
                        "decision after completed regular-session close; entry next "
                        "regular-session open; exit fifth subsequent session close"
                    ),
                    "resolution": resolution,
                    "research_only": True,
                    "execution_enabled": False,
                }
            )
    return output


def load_call_features(
    options_root: Path,
    closes: dict[tuple[str, str], float],
) -> dict[tuple[str, str], dict[str, Any]]:
    base = []
    for symbol in SYMBOLS:
        for path in sorted(options_root.glob(f"*/*/{symbol}.json.gz")):
            market_date = path.parent.name
            chain = load_chain(path)
            if not chain:
                continue
            underlying = closes.get((symbol, market_date))
            if underlying is None or underlying <= 0:
                continue
            features = option_chain_features(chain, underlying)
            if not features["option_chain_available"]:
                continue
            base.append({"symbol": symbol, "market_date": market_date, **features})
    rolling = unusual_call_features(base)
    return {
        (str(row["symbol"]), str(row["market_date"])): {
            "call_features_available": True,
            **{
                key: value
                for key, value in row.items()
                if key not in {"symbol", "market_date"}
            },
        }
        for row in rolling
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candle-root", type=Path, required=True)
    parser.add_argument("--options-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    raw = {symbol: load_symbol(args.candle_root, symbol) for symbol in SYMBOLS}
    one_minute_daily = {
        symbol: make_daily(frame, "1min") for symbol, frame in raw.items()
    }
    closes = {
        (symbol, str(row["market_date"])): float(row["close"])
        for symbol, rows in one_minute_daily.items()
        for row in rows
    }
    call_features = load_call_features(args.options_root, closes)
    args.output_root.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for resolution in RESOLUTIONS:
        daily = (
            one_minute_daily
            if resolution == "1min"
            else {
                symbol: make_daily(
                    resample_regular(frame, resolution), resolution
                )
                for symbol, frame in raw.items()
            }
        )
        rows = build_candle_rows(daily, resolution)
        for row in rows:
            overlay = call_features.get((row["symbol"], row["market_date"]))
            if overlay:
                row.update(overlay)
            else:
                row.update(
                    {
                        "call_features_available": False,
                        "call_activity_history_count": None,
                        "call_volume_vs_prior_median": None,
                        "call_volume_zscore": None,
                        "call_volume_unusual": None,
                        "call_volume_open_interest_ratio": None,
                    }
                )
        output = args.output_root / f"amd_nvda_{resolution}_five_session_panel.jsonl"
        write_jsonl(output, rows)
        outputs[resolution] = {
            "path": str(output),
            "sha256": sha256(output),
            "rows": len(rows),
            "first_date": min(row["market_date"] for row in rows),
            "last_date": max(row["market_date"] for row in rows),
            "call_rows": sum(bool(row["call_features_available"]) for row in rows),
            "unusual_call_rows": sum(row["call_volume_unusual"] is True for row in rows),
        }
    manifest = {
        "status": "complete",
        "symbols": list(SYMBOLS),
        "resolutions": list(RESOLUTIONS),
        "outputs": outputs,
        "call_feature_contract": (
            "call volume only; rolling comparison uses strictly earlier exact "
            "nonempty Alpha Vantage chains; missing chains remain unavailable"
        ),
        "research_only": True,
        "execution_enabled": False,
    }
    manifest_path = args.output_root / "panel_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
