from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from alientai_v2.engines.engine_registry import run_enabled_engines
from alientai_v2.settings import load_settings
from alientai_v2.utils import safe_float


def parse_time(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    # Keep timezone-aware ISO strings parseable.
    # Example: 2026-06-17T13:30:00+00:00
    text = text.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        return parsed
    except Exception:
        pass

    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(text[:26], fmt)
        except Exception:
            pass

    return None


def pick(row: Dict[str, Any], *names: str, default: Any = None) -> Any:
    lower_map = {str(k).lower(): k for k in row.keys()}

    for name in names:
        key = lower_map.get(name.lower())
        if key is not None:
            return row.get(key)

    return default


def load_candles(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for raw in reader:
            symbol = str(pick(raw, "symbol", "ticker", "T", default="")).upper().strip()
            ts = parse_time(pick(raw, "timestamp", "datetime", "datetime_utc", "datetime_ms", "time", "date", "t", "candle_time", "bar_time", "start_time", "started_at"))

            open_price = safe_float(pick(raw, "open", "o", default=0.0), 0.0)
            high = safe_float(pick(raw, "high", "h", default=0.0), 0.0)
            low = safe_float(pick(raw, "low", "l", default=0.0), 0.0)
            close = safe_float(pick(raw, "close", "c", "price", default=0.0), 0.0)
            volume = safe_float(pick(raw, "volume", "v", default=0.0), 0.0)

            if not symbol or ts is None or close <= 0:
                continue

            rows.append({
                "symbol": symbol,
                "timestamp": ts,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            })

    rows.sort(key=lambda r: (r["symbol"], r["timestamp"]))
    return rows


def build_quote_from_candle(
    candle: Dict[str, Any],
    previous_close: Optional[float],
    average_volume: Optional[float],
) -> Dict[str, Any]:
    close = safe_float(candle.get("close"), 0.0)
    open_price = safe_float(candle.get("open"), close)
    volume = safe_float(candle.get("volume"), 0.0)

    base = previous_close if previous_close and previous_close > 0 else open_price
    move_pct = ((close - base) / base) * 100.0 if base else 0.0

    rv = 1.0
    if average_volume and average_volume > 0:
        rv = volume / average_volume

    spread_percent = 0.05

    return {
        "symbol": candle["symbol"],
        "price": close,
        "net_change_percent": round(move_pct, 4),
        "relative_volume": round(rv, 4),
        "spread_percent": spread_percent,
        "volume": volume,
        "bid": round(close * 0.99975, 4),
        "ask": round(close * 1.00025, 4),
        "close": base,
        "source": "historical_replay_candle",
        "timestamp": candle["timestamp"].isoformat(),
    }


def future_close_for_horizon(
    candles_by_symbol: Dict[str, List[Dict[str, Any]]],
    symbol: str,
    entry_time: datetime,
    horizon_minutes: float,
) -> Optional[Dict[str, Any]]:
    future_target = entry_time + timedelta(minutes=float(horizon_minutes))

    rows = candles_by_symbol.get(symbol, [])

    for row in rows:
        if row["timestamp"] >= future_target:
            return row

    return None


def run_replay(path: Path, max_rows: int = 0) -> Dict[str, Any]:
    settings = load_settings()
    candles = load_candles(path)

    if max_rows and max_rows > 0:
        candles = candles[:max_rows]

    candles_by_symbol: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in candles:
        candles_by_symbol[row["symbol"]].append(row)

    previous_close_by_symbol: Dict[str, float] = {}
    recent_volumes_by_symbol: Dict[str, List[float]] = defaultdict(list)

    trades: List[Dict[str, Any]] = []
    candidate_count = 0

    for candle in candles:
        symbol = candle["symbol"]

        recent_vols = recent_volumes_by_symbol[symbol]
        avg_vol = sum(recent_vols[-20:]) / len(recent_vols[-20:]) if recent_vols else None

        quote = build_quote_from_candle(
            candle,
            previous_close=previous_close_by_symbol.get(symbol),
            average_volume=avg_vol,
        )

        candidates = run_enabled_engines([quote], settings)

        for candidate in candidates:
            candidate_count += 1

            if candidate.get("decision") not in {"BUY_CANDIDATE", "STRONG_BUY_CANDIDATE"}:
                continue

            horizon_minutes = safe_float(candidate.get("prediction_horizon_minutes"), 0.0)

            if horizon_minutes <= 0:
                continue

            future = future_close_for_horizon(
                candles_by_symbol,
                symbol,
                candle["timestamp"],
                horizon_minutes,
            )

            if future is None:
                outcome_available = False
                future_price = None
                pnl_pct = None
                win = None
            else:
                outcome_available = True
                future_price = safe_float(future.get("close"), 0.0)
                entry_price = safe_float(candidate.get("price"), 0.0)
                pnl_pct = ((future_price - entry_price) / entry_price) * 100.0 if entry_price else 0.0
                win = pnl_pct > 0

            trades.append({
                "engine_id": candidate.get("engine_id"),
                "symbol": symbol,
                "entry_time": candle["timestamp"].isoformat(),
                "entry_price": candidate.get("price"),
                "score": candidate.get("score"),
                "decision": candidate.get("decision"),
                "prediction_horizon_minutes": horizon_minutes,
                "prediction_horizon_days": candidate.get("prediction_horizon_days"),
                "future_price": future_price,
                "outcome_available": outcome_available,
                "pnl_pct": round(pnl_pct, 4) if pnl_pct is not None else None,
                "win": win,
                "reason": candidate.get("reason"),
                "reasons": candidate.get("reasons", []),
                "warnings": candidate.get("warnings", []),
            })

        previous_close_by_symbol[symbol] = safe_float(candle.get("close"), 0.0)
        recent_volumes_by_symbol[symbol].append(safe_float(candle.get("volume"), 0.0))

    summary_by_engine: Dict[str, Dict[str, Any]] = {}

    for trade in trades:
        engine_id = str(trade.get("engine_id"))
        bucket = summary_by_engine.setdefault(engine_id, {
            "engine_id": engine_id,
            "trades": 0,
            "outcomes_available": 0,
            "wins": 0,
            "losses": 0,
            "avg_pnl_pct": 0.0,
            "total_pnl_pct_points": 0.0,
        })

        bucket["trades"] += 1

        if trade.get("outcome_available"):
            bucket["outcomes_available"] += 1
            pnl = safe_float(trade.get("pnl_pct"), 0.0)
            bucket["total_pnl_pct_points"] += pnl

            if trade.get("win"):
                bucket["wins"] += 1
            else:
                bucket["losses"] += 1

    for bucket in summary_by_engine.values():
        n = bucket["outcomes_available"]

        if n:
            bucket["avg_pnl_pct"] = round(bucket["total_pnl_pct_points"] / n, 4)
            bucket["win_rate_pct"] = round(bucket["wins"] / n * 100.0, 2)
        else:
            bucket["avg_pnl_pct"] = None
            bucket["win_rate_pct"] = None

        bucket.pop("total_pnl_pct_points", None)

    report = {
        "status": "success",
        "mode": "historical_replay_does_not_touch_live_paper_account",
        "input_file": str(path),
        "candles_loaded": len(candles),
        "candidate_rows_scanned": candidate_count,
        "buy_candidates_found": len(trades),
        "enabled_engines": settings.get("enabled_engines"),
        "summary_by_engine": list(summary_by_engine.values()),
        "sample_trades": trades[:50],
    }

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to historical candle CSV.")
    parser.add_argument("--max-rows", type=int, default=0, help="Optional row limit for fast testing.")
    parser.add_argument("--out", default="data_v2/v2_historical_replay_report.json")

    args = parser.parse_args()

    report = run_replay(Path(args.csv), max_rows=args.max_rows)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": report["status"],
        "input_file": report["input_file"],
        "candles_loaded": report["candles_loaded"],
        "candidate_rows_scanned": report["candidate_rows_scanned"],
        "buy_candidates_found": report["buy_candidates_found"],
        "summary_by_engine": report["summary_by_engine"],
        "out": str(out_path),
    }, indent=2))


if __name__ == "__main__":
    main()

