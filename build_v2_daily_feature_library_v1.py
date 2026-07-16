import argparse
import csv
import json
import math
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from supabase import create_client
except Exception as exc:
    raise SystemExit("Missing supabase package. Install/activate your project venv first.") from exc


BUILD = "ALIENTAI_V2_DAILY_FEATURE_LIBRARY_BUILDER_V1"
PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data_v2" / "training_library" / "daily_features_v1"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def read_symbols_file(path: Path) -> List[str]:
    symbols = []
    seen = set()

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.replace("\ufeff", "").strip().upper()
        if not s or s.startswith("#"):
            continue
        if "," in s:
            s = s.split(",", 1)[0].replace("\ufeff", "").strip().upper()
        if s and s not in seen:
            seen.add(s)
            symbols.append(s)

    return symbols


def make_supabase_client():
    if load_dotenv:
        load_dotenv(PROJECT_ROOT / ".env")

    url = os.getenv("SUPABASE_URL") or os.getenv("SUPABASE_PROJECT_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_PUBLISHABLE_KEY")
    )

    if not url or not key:
        raise SystemExit("Missing SUPABASE_URL and/or SUPABASE key in .env")

    return create_client(url, key)


def fetch_daily_candles(
    sb,
    *,
    table: str,
    symbol: str,
    candle_limit: int,
    page_size: int = 1000,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    start = 0

    while True:
        end = start + page_size - 1

        resp = (
            sb.table(table)
            .select("symbol,date,datetime_ms,datetime_utc,open,high,low,close,volume,timeframe")
            .eq("symbol", symbol)
            .eq("timeframe", "1d")
            .order("datetime_ms", desc=False)
            .range(start, end)
            .execute()
        )

        batch = resp.data or []
        if not batch:
            break

        rows.extend(batch)

        if len(batch) < page_size:
            break

        if candle_limit and len(rows) >= candle_limit:
            rows = rows[-candle_limit:]
            break

        start += page_size

    # Deduplicate by datetime_ms. This protects us if old and new uploads overlapped.
    by_time: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        dt = safe_int(r.get("datetime_ms"), 0)
        if dt > 0:
            by_time[dt] = r

    clean = list(by_time.values())
    clean.sort(key=lambda r: safe_int(r.get("datetime_ms"), 0))

    if candle_limit and len(clean) > candle_limit:
        clean = clean[-candle_limit:]

    return clean


def sma(values: List[float], index: int, length: int) -> Optional[float]:
    if index + 1 < length:
        return None
    window = values[index - length + 1:index + 1]
    if not window:
        return None
    return sum(window) / len(window)


def rolling_high(values: List[float], index: int, length: int) -> Optional[float]:
    if index + 1 < length:
        return None
    return max(values[index - length + 1:index + 1])


def rolling_low(values: List[float], index: int, length: int) -> Optional[float]:
    if index + 1 < length:
        return None
    return min(values[index - length + 1:index + 1])


def ema_series(values: List[float], length: int) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(values)
    if len(values) < length:
        return out

    alpha = 2.0 / (length + 1.0)
    first = sum(values[:length]) / length
    out[length - 1] = first

    prev = first
    for i in range(length, len(values)):
        prev = values[i] * alpha + prev * (1.0 - alpha)
        out[i] = prev

    return out


def rsi14_series(closes: List[float], length: int = 14) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(closes)
    if len(closes) <= length:
        return out

    gains = [0.0]
    losses = [0.0]

    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    for i in range(length, len(closes)):
        avg_gain = sum(gains[i - length + 1:i + 1]) / length
        avg_loss = sum(losses[i - length + 1:i + 1]) / length

        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100.0 - (100.0 / (1.0 + rs))

    return out


def atr14_series(highs: List[float], lows: List[float], closes: List[float], length: int = 14) -> List[Optional[float]]:
    tr_values: List[float] = []

    for i in range(len(closes)):
        if i == 0:
            tr = highs[i] - lows[i]
        else:
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        tr_values.append(tr)

    out: List[Optional[float]] = [None] * len(closes)
    for i in range(length - 1, len(closes)):
        out[i] = sum(tr_values[i - length + 1:i + 1]) / length

    return out


def pct_change(current: float, previous: float) -> Optional[float]:
    if previous == 0:
        return None
    return ((current / previous) - 1.0) * 100.0


def round_or_none(value: Optional[float], digits: int = 6):
    if value is None:
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return round(value, digits)


def build_symbol_features(
    symbol: str,
    candles: List[Dict[str, Any]],
    *,
    min_history_days: int,
    horizon_days: int,
) -> Dict[str, Any]:
    if len(candles) < min_history_days + horizon_days:
        return {
            "symbol": symbol,
            "status": "too_few_candles",
            "candles": len(candles),
            "features": [],
        }

    opens = [safe_float(r.get("open"), 0.0) for r in candles]
    highs = [safe_float(r.get("high"), 0.0) for r in candles]
    lows = [safe_float(r.get("low"), 0.0) for r in candles]
    closes = [safe_float(r.get("close"), 0.0) for r in candles]
    volumes = [safe_float(r.get("volume"), 0.0) for r in candles]

    ema12 = ema_series(closes, 12)
    ema26 = ema_series(closes, 26)

    macd_line: List[Optional[float]] = []
    for i in range(len(closes)):
        if ema12[i] is None or ema26[i] is None:
            macd_line.append(None)
        else:
            macd_line.append(ema12[i] - ema26[i])

    # For MACD signal, use 0 filler for None period but only trust after enough history.
    macd_for_signal = [x if x is not None else 0.0 for x in macd_line]
    macd_signal = ema_series(macd_for_signal, 9)

    rsi14 = rsi14_series(closes, 14)
    atr14 = atr14_series(highs, lows, closes, 14)

    rows = []

    start_index = max(200, min_history_days)

    # Stop before future target would go past the data end.
    stop_index = len(candles) - horizon_days

    for i in range(start_index, stop_index):
        close = closes[i]
        if close <= 0:
            continue

        prev_close = closes[i - 1] if i >= 1 else 0.0
        future_close = closes[i + horizon_days]

        sma20 = sma(closes, i, 20)
        sma50 = sma(closes, i, 50)
        sma200 = sma(closes, i, 200)
        vol20 = sma(volumes, i, 20)

        high20 = rolling_high(highs, i, 20)
        low20 = rolling_low(lows, i, 20)
        high60 = rolling_high(highs, i, 60)
        low60 = rolling_low(lows, i, 60)

        macd_hist = None
        if macd_line[i] is not None and macd_signal[i] is not None:
            macd_hist = macd_line[i] - macd_signal[i]

        target_return = pct_change(future_close, close)
        if target_return is None:
            continue

        row = {
            "build": BUILD,
            "symbol": symbol,
            "date": str(candles[i].get("date") or ""),
            "datetime_ms": safe_int(candles[i].get("datetime_ms"), 0),

            # Raw candle reference values. Engines may use them or ignore them.
            "open": round_or_none(opens[i]),
            "high": round_or_none(highs[i]),
            "low": round_or_none(lows[i]),
            "close": round_or_none(close),
            "volume": safe_int(volumes[i], 0),

            # Normalized returns.
            "return_1d_pct": round_or_none(pct_change(close, closes[i - 1]) if i >= 1 else None),
            "return_5d_pct": round_or_none(pct_change(close, closes[i - 5]) if i >= 5 else None),
            "return_20d_pct": round_or_none(pct_change(close, closes[i - 20]) if i >= 20 else None),
            "return_60d_pct": round_or_none(pct_change(close, closes[i - 60]) if i >= 60 else None),

            # Candle shape.
            "range_pct": round_or_none(((highs[i] - lows[i]) / close) * 100.0 if close else None),
            "body_pct": round_or_none(((close - opens[i]) / close) * 100.0 if close else None),
            "gap_pct": round_or_none(((opens[i] - prev_close) / prev_close) * 100.0 if prev_close else None),

            # Volume.
            "volume_sma20": round_or_none(vol20),
            "volume_ratio_20d": round_or_none((volumes[i] / vol20) if vol20 and vol20 > 0 else None),

            # Moving averages.
            "sma20": round_or_none(sma20),
            "sma50": round_or_none(sma50),
            "sma200": round_or_none(sma200),
            "close_vs_sma20_pct": round_or_none(((close / sma20) - 1.0) * 100.0 if sma20 else None),
            "close_vs_sma50_pct": round_or_none(((close / sma50) - 1.0) * 100.0 if sma50 else None),
            "close_vs_sma200_pct": round_or_none(((close / sma200) - 1.0) * 100.0 if sma200 else None),

            # Momentum/volatility indicators.
            "rsi14": round_or_none(rsi14[i]),
            "macd_line": round_or_none(macd_line[i]),
            "macd_signal": round_or_none(macd_signal[i]),
            "macd_hist": round_or_none(macd_hist),
            "atr14": round_or_none(atr14[i]),
            "atr14_pct": round_or_none((atr14[i] / close) * 100.0 if atr14[i] and close else None),

            # Position within recent ranges.
            "distance_from_20d_high_pct": round_or_none(((close / high20) - 1.0) * 100.0 if high20 else None),
            "distance_from_20d_low_pct": round_or_none(((close / low20) - 1.0) * 100.0 if low20 else None),
            "distance_from_60d_high_pct": round_or_none(((close / high60) - 1.0) * 100.0 if high60 else None),
            "distance_from_60d_low_pct": round_or_none(((close / low60) - 1.0) * 100.0 if low60 else None),

            # Training labels. These use future data and must never be used as input features.
            "target_horizon_days": horizon_days,
            "target_future_close": round_or_none(future_close),
            "target_return_20d_pct": round_or_none(target_return),
            "target_up_20d": bool(target_return > 0),
            "target_strong_up_20d": bool(target_return >= 3.0),
            "target_down_20d": bool(target_return < 0),
            "target_strong_down_20d": bool(target_return <= -3.0),
        }

        rows.append(row)

    return {
        "symbol": symbol,
        "status": "success" if rows else "no_feature_rows",
        "candles": len(candles),
        "feature_rows": len(rows),
        "features": rows,
    }


def append_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")


def write_summary_csv(path: Path, summaries: List[Dict[str, Any]]) -> None:
    fieldnames = [
        "symbol",
        "status",
        "candles",
        "feature_rows",
        "first_date",
        "last_date",
        "avg_target_return_20d_pct",
        "target_up_rate_20d_pct",
        "target_strong_up_rate_20d_pct",
        "target_strong_down_rate_20d_pct",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summaries:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def summarize_feature_rows(symbol: str, status: str, candles: int, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {
            "symbol": symbol,
            "status": status,
            "candles": candles,
            "feature_rows": 0,
        }

    returns = [safe_float(r.get("target_return_20d_pct"), 0.0) for r in rows]
    up = [1 for r in rows if r.get("target_up_20d")]
    strong_up = [1 for r in rows if r.get("target_strong_up_20d")]
    strong_down = [1 for r in rows if r.get("target_strong_down_20d")]

    total = len(rows)

    return {
        "symbol": symbol,
        "status": status,
        "candles": candles,
        "feature_rows": total,
        "first_date": rows[0].get("date"),
        "last_date": rows[-1].get("date"),
        "avg_target_return_20d_pct": round(sum(returns) / total, 6) if total else None,
        "target_up_rate_20d_pct": round((len(up) / total) * 100.0, 4) if total else None,
        "target_strong_up_rate_20d_pct": round((len(strong_up) / total) * 100.0, 4) if total else None,
        "target_strong_down_rate_20d_pct": round((len(strong_down) / total) * 100.0, 4) if total else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Build AlientAI V2 daily training feature library from Supabase daily candles.")
    parser.add_argument("--table", default="v2_daily_candles")
    parser.add_argument("--symbols-file", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run-name", default="")
    parser.add_argument("--limit-symbols", type=int, default=0)
    parser.add_argument("--candle-limit", type=int, default=10000)
    parser.add_argument("--min-history-days", type=int, default=220)
    parser.add_argument("--horizon-days", type=int, default=20)
    parser.add_argument("--delay", type=float, default=0.02)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    symbols_path = Path(args.symbols_file)
    if not symbols_path.exists():
        raise SystemExit(f"Missing symbols file: {symbols_path}")

    symbols = read_symbols_file(symbols_path)
    if args.limit_symbols and args.limit_symbols > 0:
        symbols = symbols[:args.limit_symbols]

    output_dir = Path(args.output_dir)
    if args.run_name:
        output_dir = output_dir / args.run_name

    output_dir.mkdir(parents=True, exist_ok=True)

    rows_path = output_dir / "daily_feature_rows.jsonl"
    summary_csv_path = output_dir / "daily_feature_summary.csv"
    summary_json_path = output_dir / "daily_feature_summary.json"
    allow_symbols_path = output_dir / "daily_feature_symbols_ready.txt"
    rejected_symbols_path = output_dir / "daily_feature_symbols_rejected.txt"

    if args.overwrite and rows_path.exists():
        rows_path.unlink()

    if rows_path.exists() and not args.overwrite:
        raise SystemExit(f"{rows_path} already exists. Use --overwrite or a new --run-name.")

    sb = make_supabase_client()

    print("Build:", BUILD)
    print("Symbols file:", symbols_path)
    print("Symbols:", len(symbols))
    print("Table:", args.table)
    print("Output dir:", output_dir)
    print("Candle limit:", args.candle_limit)
    print("Min history days:", args.min_history_days)
    print("Horizon days:", args.horizon_days)
    print("This does NOT touch the V2 paper account.")
    print("")

    summaries = []
    ready_symbols = []
    rejected_symbols = []
    total_feature_rows = 0

    for idx, symbol in enumerate(symbols, start=1):
        print(f"[{idx}/{len(symbols)}] Building features for {symbol}...")

        try:
            candles = fetch_daily_candles(
                sb,
                table=args.table,
                symbol=symbol,
                candle_limit=args.candle_limit,
            )

            result = build_symbol_features(
                symbol,
                candles,
                min_history_days=args.min_history_days,
                horizon_days=args.horizon_days,
            )

            features = result.get("features", [])
            status = result.get("status", "unknown")
            candles_count = int(result.get("candles", 0) or 0)

            if features:
                append_jsonl(rows_path, features)
                ready_symbols.append(symbol)
                total_feature_rows += len(features)
                print(f"  success | candles={candles_count} feature_rows={len(features)}")
            else:
                rejected_symbols.append(symbol)
                print(f"  {status} | candles={candles_count} feature_rows=0")

            summaries.append(summarize_feature_rows(symbol, status, candles_count, features))

        except Exception as exc:
            rejected_symbols.append(symbol)
            summaries.append({
                "symbol": symbol,
                "status": "error",
                "candles": 0,
                "feature_rows": 0,
                "error": str(exc),
            })
            print(f"  ERROR {symbol}: {exc}")

        if args.delay:
            time.sleep(args.delay)

    write_summary_csv(summary_csv_path, summaries)

    ready_symbols.sort()
    rejected_symbols.sort()

    allow_symbols_path.write_text("\n".join(ready_symbols) + ("\n" if ready_symbols else ""), encoding="utf-8")
    rejected_symbols_path.write_text("\n".join(rejected_symbols) + ("\n" if rejected_symbols else ""), encoding="utf-8")

    report = {
        "status": "complete",
        "finished_at": now_iso(),
        "build": BUILD,
        "table": args.table,
        "symbols_file": str(symbols_path),
        "symbols_seen": len(symbols),
        "symbols_ready": len(ready_symbols),
        "symbols_rejected": len(rejected_symbols),
        "total_feature_rows": total_feature_rows,
        "output_dir": str(output_dir),
        "rows_path": str(rows_path),
        "summary_csv": str(summary_csv_path),
        "summary_json": str(summary_json_path),
        "ready_symbols_path": str(allow_symbols_path),
        "rejected_symbols_path": str(rejected_symbols_path),
        "settings": {
            "candle_limit": args.candle_limit,
            "min_history_days": args.min_history_days,
            "horizon_days": args.horizon_days,
        },
    }

    summary_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("")
    print("DONE")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
