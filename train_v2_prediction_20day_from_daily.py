from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


BUILD = "ALIENTAI_V2_PREDICTION_20DAY_DAILY_TRAINER_V1"

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_TABLE = "v2_daily_candles"
OUT_DIR = PROJECT_ROOT / "data_v2" / "prediction_20day_daily_training"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and value:
            os.environ[key] = value


def env_value(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)

        if value:
            return value

    return ""


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def pct_change(old: float, new: float) -> float:
    old = safe_float(old, 0.0)
    new = safe_float(new, 0.0)

    if old <= 0:
        return 0.0

    return ((new - old) / old) * 100.0


def mean(values: List[float], default: float = 0.0) -> float:
    values = [safe_float(v, 0.0) for v in values if v is not None]

    if not values:
        return default

    return sum(values) / len(values)


def stdev(values: List[float], default: float = 0.0) -> float:
    values = [safe_float(v, 0.0) for v in values if v is not None]

    if len(values) < 2:
        return default

    try:
        return statistics.stdev(values)
    except Exception:
        return default


def supabase_headers(key: str) -> Dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def supabase_get(
    *,
    supabase_url: str,
    supabase_key: str,
    table: str,
    params: Dict[str, str],
    timeout: int = 90,
) -> List[Dict[str, Any]]:
    url = supabase_url.rstrip("/") + f"/rest/v1/{table}"

    response = requests.get(
        url,
        headers=supabase_headers(supabase_key),
        params=params,
        timeout=timeout,
    )

    if response.status_code not in {200, 206}:
        raise RuntimeError(f"Supabase HTTP {response.status_code}: {response.text[:1000]}")

    return response.json()


def read_symbols_file(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Symbols file not found: {path}")

    symbols: List[str] = []

    for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        symbol = line.strip().upper()

        if not symbol or symbol.startswith("#"):
            continue

        symbols.append(symbol)

    return sorted(set(symbols))


def fetch_symbols_from_daily_table(
    *,
    supabase_url: str,
    supabase_key: str,
    table: str,
    limit: int,
) -> List[str]:
    """
    Simple symbol discovery from daily table.

    Because each daily symbol has thousands of rows, this may not find every symbol
    if the first page is dominated by early alphabet symbols. For reliable runs,
    prefer --symbols-file v2_live_watchlist_symbols.txt.
    """
    rows = supabase_get(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        table=table,
        params={
            "select": "symbol",
            "order": "symbol.asc",
            "limit": "20000",
        },
    )

    symbols = sorted(set(str(r.get("symbol") or "").upper().strip() for r in rows if r.get("symbol")))

    if limit and limit > 0:
        symbols = symbols[:limit]

    return symbols


def fetch_daily_candles(
    *,
    supabase_url: str,
    supabase_key: str,
    table: str,
    symbol: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Fetch daily candles in pages.

    PostgREST can cap large responses, so this uses a datetime_ms cursor.
    Fetch newest-to-oldest, then sort oldest-to-newest.
    """
    symbol = str(symbol or "").upper().strip()

    all_rows: List[Dict[str, Any]] = []
    page_size = 1000
    before_ms: Optional[int] = None

    while len(all_rows) < limit:
        remaining = limit - len(all_rows)
        this_limit = min(page_size, remaining)

        params = {
            "select": "symbol,timeframe,datetime_ms,datetime_utc,date,open,high,low,close,volume",
            "symbol": f"eq.{symbol}",
            "timeframe": "eq.1d",
            "order": "datetime_ms.desc",
            "limit": str(this_limit),
        }

        if before_ms is not None:
            params["datetime_ms"] = f"lt.{before_ms}"

        rows = supabase_get(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            table=table,
            params=params,
        )

        if not rows:
            break

        all_rows.extend(rows)

        page_min_ms = min(safe_int(r.get("datetime_ms"), 0) for r in rows)

        if page_min_ms <= 0:
            break

        before_ms = page_min_ms

        if len(rows) < this_limit:
            break

        time.sleep(0.02)

    candles: List[Dict[str, Any]] = []
    seen = set()

    for raw in all_rows:
        datetime_ms = safe_int(raw.get("datetime_ms"), 0)

        if datetime_ms <= 0:
            continue

        key = (symbol, datetime_ms)

        if key in seen:
            continue

        seen.add(key)

        candles.append({
            "symbol": symbol,
            "timeframe": "1d",
            "datetime_ms": datetime_ms,
            "datetime_utc": str(raw.get("datetime_utc") or ""),
            "date": str(raw.get("date") or ""),
            "open": safe_float(raw.get("open"), 0.0),
            "high": safe_float(raw.get("high"), 0.0),
            "low": safe_float(raw.get("low"), 0.0),
            "close": safe_float(raw.get("close"), 0.0),
            "volume": safe_float(raw.get("volume"), 0.0),
        })

    candles.sort(key=lambda r: int(r.get("datetime_ms") or 0))
    return candles


def trailing_returns(closes: List[float], idx: int, days: int) -> float:
    if idx - days < 0:
        return 0.0

    return pct_change(closes[idx - days], closes[idx])


def sma(values: List[float], idx: int, days: int) -> float:
    if idx - days + 1 < 0:
        return 0.0

    return mean(values[idx - days + 1:idx + 1], 0.0)


def rolling_high(values: List[float], idx: int, days: int) -> float:
    if idx - days + 1 < 0:
        return 0.0

    return max(values[idx - days + 1:idx + 1])


def rolling_low(values: List[float], idx: int, days: int) -> float:
    if idx - days + 1 < 0:
        return 0.0

    return min(values[idx - days + 1:idx + 1])


def rolling_daily_returns(closes: List[float], idx: int, days: int) -> List[float]:
    start = max(1, idx - days + 1)
    returns: List[float] = []

    for i in range(start, idx + 1):
        returns.append(pct_change(closes[i - 1], closes[i]))

    return returns


def build_daily_features(candles: List[Dict[str, Any]], idx: int) -> Dict[str, float]:
    closes = [safe_float(c.get("close"), 0.0) for c in candles]
    highs = [safe_float(c.get("high"), 0.0) for c in candles]
    lows = [safe_float(c.get("low"), 0.0) for c in candles]
    volumes = [safe_float(c.get("volume"), 0.0) for c in candles]

    close = closes[idx]

    if close <= 0:
        return {}

    sma20 = sma(closes, idx, 20)
    sma50 = sma(closes, idx, 50)
    sma100 = sma(closes, idx, 100)
    sma200 = sma(closes, idx, 200)

    high20 = rolling_high(highs, idx, 20)
    high50 = rolling_high(highs, idx, 50)
    high200 = rolling_high(highs, idx, 200)

    low20 = rolling_low(lows, idx, 20)
    low50 = rolling_low(lows, idx, 50)

    volume20 = sma(volumes, idx, 20)
    volume50 = sma(volumes, idx, 50)

    returns20 = rolling_daily_returns(closes, idx, 20)
    returns50 = rolling_daily_returns(closes, idx, 50)

    drawdown20 = 0.0
    if high20 > 0:
        drawdown20 = ((close - high20) / high20) * 100.0

    drawdown50 = 0.0
    if high50 > 0:
        drawdown50 = ((close - high50) / high50) * 100.0

    position_vs_20_high = 0.0
    if high20 > 0:
        position_vs_20_high = close / high20

    position_vs_50_high = 0.0
    if high50 > 0:
        position_vs_50_high = close / high50

    position_vs_200_high = 0.0
    if high200 > 0:
        position_vs_200_high = close / high200

    position_in_20_range = 0.5
    if high20 > low20:
        position_in_20_range = (close - low20) / (high20 - low20)

    position_in_50_range = 0.5
    if high50 > low50:
        position_in_50_range = (close - low50) / (high50 - low50)

    volume_ratio_20_50 = 1.0
    if volume50 > 0:
        volume_ratio_20_50 = volume20 / volume50

    features = {
        "return_5d": trailing_returns(closes, idx, 5),
        "return_10d": trailing_returns(closes, idx, 10),
        "return_20d": trailing_returns(closes, idx, 20),
        "return_50d": trailing_returns(closes, idx, 50),
        "return_100d": trailing_returns(closes, idx, 100),
        "return_200d": trailing_returns(closes, idx, 200),

        "above_sma20": 1.0 if sma20 > 0 and close > sma20 else 0.0,
        "above_sma50": 1.0 if sma50 > 0 and close > sma50 else 0.0,
        "above_sma100": 1.0 if sma100 > 0 and close > sma100 else 0.0,
        "above_sma200": 1.0 if sma200 > 0 and close > sma200 else 0.0,

        "sma20_vs_sma50_pct": pct_change(sma50, sma20) if sma50 > 0 and sma20 > 0 else 0.0,
        "sma50_vs_sma200_pct": pct_change(sma200, sma50) if sma200 > 0 and sma50 > 0 else 0.0,

        "drawdown20_pct": drawdown20,
        "drawdown50_pct": drawdown50,
        "position_vs_20_high": position_vs_20_high,
        "position_vs_50_high": position_vs_50_high,
        "position_vs_200_high": position_vs_200_high,
        "position_in_20_range": position_in_20_range,
        "position_in_50_range": position_in_50_range,

        "volatility_20d": stdev(returns20, 0.0),
        "volatility_50d": stdev(returns50, 0.0),

        "volume_ratio_20_50": volume_ratio_20_50,
    }

    return {k: round(safe_float(v, 0.0), 6) for k, v in features.items()}


def future_outcome_20d(candles: List[Dict[str, Any]], idx: int, horizon_days: int) -> Dict[str, Any]:
    if idx + horizon_days >= len(candles):
        return {}

    entry_close = safe_float(candles[idx].get("close"), 0.0)
    future_close = safe_float(candles[idx + horizon_days].get("close"), 0.0)

    if entry_close <= 0 or future_close <= 0:
        return {}

    future_slice = candles[idx + 1:idx + horizon_days + 1]

    future_high = max(safe_float(c.get("high"), 0.0) for c in future_slice)
    future_low = min(safe_float(c.get("low"), 0.0) for c in future_slice)

    future_return = pct_change(entry_close, future_close)
    max_gain = pct_change(entry_close, future_high)
    max_drawdown = pct_change(entry_close, future_low)

    return {
        "future_close": future_close,
        "future_return_pct": round(future_return, 6),
        "future_up": future_return > 0,
        "max_gain_pct": round(max_gain, 6),
        "max_drawdown_pct": round(max_drawdown, 6),
    }


def score_features(features: Dict[str, float]) -> float:
    """
    Simple transparent score for 20-day candidates.

    This is not machine learning yet. It is a trainable baseline score.
    We replay it through history to see which symbols actually work.
    """
    score = 0.0

    # Momentum stack.
    score += max(-10.0, min(15.0, features.get("return_5d", 0.0) * 1.5))
    score += max(-10.0, min(15.0, features.get("return_10d", 0.0) * 1.0))
    score += max(-15.0, min(20.0, features.get("return_20d", 0.0) * 0.8))
    score += max(-10.0, min(15.0, features.get("return_50d", 0.0) * 0.25))

    # Trend alignment.
    score += 8.0 if features.get("above_sma20", 0.0) >= 1.0 else -4.0
    score += 8.0 if features.get("above_sma50", 0.0) >= 1.0 else -4.0
    score += 5.0 if features.get("above_sma200", 0.0) >= 1.0 else -2.0

    score += max(-5.0, min(8.0, features.get("sma20_vs_sma50_pct", 0.0)))
    score += max(-5.0, min(8.0, features.get("sma50_vs_sma200_pct", 0.0) * 0.5))

    # Breakout position.
    pos20 = features.get("position_vs_20_high", 0.0)
    pos50 = features.get("position_vs_50_high", 0.0)

    if pos20 >= 0.98:
        score += 8.0
    elif pos20 >= 0.95:
        score += 4.0

    if pos50 >= 0.98:
        score += 6.0
    elif pos50 >= 0.95:
        score += 3.0

    # Avoid too deep drawdowns.
    dd20 = features.get("drawdown20_pct", 0.0)
    dd50 = features.get("drawdown50_pct", 0.0)

    if dd20 < -12.0:
        score -= 8.0
    elif dd20 < -7.0:
        score -= 4.0

    if dd50 < -20.0:
        score -= 6.0

    # Volume confirmation.
    volume_ratio = features.get("volume_ratio_20_50", 1.0)

    if volume_ratio >= 1.25:
        score += 5.0
    elif volume_ratio >= 1.05:
        score += 2.0
    elif volume_ratio < 0.75:
        score -= 3.0

    # Volatility penalty: too wild is dangerous for 20-day hold.
    vol20 = features.get("volatility_20d", 0.0)

    if vol20 > 6.0:
        score -= 8.0
    elif vol20 > 4.0:
        score -= 4.0

    return round(max(0.0, min(100.0, score)), 4)


def decision_from_score(score: float, buy_score: float, watch_score: float) -> str:
    if score >= buy_score:
        return "BUY_CANDIDATE"

    if score >= watch_score:
        return "WATCH"

    return "AVOID"


def append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, separators=(",", ":")) + "\n")


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def train_symbol(
    *,
    symbol: str,
    candles: List[Dict[str, Any]],
    records_path: Path,
    min_history_days: int,
    horizon_days: int,
    step_days: int,
    max_windows_per_symbol: int,
    buy_score: float,
    watch_score: float,
) -> Dict[str, Any]:
    required = min_history_days + horizon_days + 1

    if len(candles) < required:
        return {
            "symbol": symbol,
            "status": "too_few_candles",
            "candles": len(candles),
            "records": 0,
            "buy_candidates": 0,
            "watch": 0,
            "avoid": 0,
            "buy_candidate_win_rate_pct": "",
            "watch_or_buy_win_rate_pct": "",
            "avg_future_20d_return_pct": "",
            "avg_buy_future_20d_return_pct": "",
            "avg_score": "",
        }

    start_idx = min_history_days
    end_idx = len(candles) - horizon_days - 1

    indices = list(range(start_idx, end_idx, step_days))

    if max_windows_per_symbol > 0 and len(indices) > max_windows_per_symbol:
        stride = max(1, math.floor(len(indices) / max_windows_per_symbol))
        indices = indices[::stride][:max_windows_per_symbol]

    records = 0
    buy_candidates = 0
    watch = 0
    avoid = 0

    buy_wins = 0
    watch_or_buy_count = 0
    watch_or_buy_wins = 0

    all_returns: List[float] = []
    buy_returns: List[float] = []
    scores: List[float] = []

    for idx in indices:
        features = build_daily_features(candles, idx)

        if not features:
            continue

        outcome = future_outcome_20d(candles, idx, horizon_days)

        if not outcome:
            continue

        score = score_features(features)
        decision = decision_from_score(score, buy_score, watch_score)

        future_return = safe_float(outcome.get("future_return_pct"), 0.0)
        future_up = bool(outcome.get("future_up"))

        if decision == "BUY_CANDIDATE":
            buy_candidates += 1
            buy_returns.append(future_return)

            if future_up:
                buy_wins += 1

        elif decision == "WATCH":
            watch += 1
        else:
            avoid += 1

        if decision in {"BUY_CANDIDATE", "WATCH"}:
            watch_or_buy_count += 1

            if future_up:
                watch_or_buy_wins += 1

        all_returns.append(future_return)
        scores.append(score)

        record = {
            "build": BUILD,
            "symbol": symbol,
            "prediction_date": candles[idx].get("date"),
            "prediction_datetime_ms": candles[idx].get("datetime_ms"),
            "close": safe_float(candles[idx].get("close"), 0.0),
            "decision": decision,
            "score": score,
            "features": features,
            "horizon_days": horizon_days,
            "future_return_pct": future_return,
            "future_up": future_up,
            "future_max_gain_pct": safe_float(outcome.get("max_gain_pct"), 0.0),
            "future_max_drawdown_pct": safe_float(outcome.get("max_drawdown_pct"), 0.0),
            "history_source": "supabase_daily",
        }

        append_jsonl(records_path, record)
        records += 1

    buy_win_rate = ""
    if buy_candidates > 0:
        buy_win_rate = round((buy_wins / buy_candidates) * 100.0, 2)

    watch_or_buy_win_rate = ""
    if watch_or_buy_count > 0:
        watch_or_buy_win_rate = round((watch_or_buy_wins / watch_or_buy_count) * 100.0, 2)

    avg_future = ""
    if all_returns:
        avg_future = round(mean(all_returns), 4)

    avg_buy_future = ""
    if buy_returns:
        avg_buy_future = round(mean(buy_returns), 4)

    avg_score = ""
    if scores:
        avg_score = round(mean(scores), 4)

    return {
        "symbol": symbol,
        "status": "success",
        "candles": len(candles),
        "records": records,
        "buy_candidates": buy_candidates,
        "watch": watch,
        "avoid": avoid,
        "buy_candidate_win_rate_pct": buy_win_rate,
        "watch_or_buy_win_rate_pct": watch_or_buy_win_rate,
        "avg_future_20d_return_pct": avg_future,
        "avg_buy_future_20d_return_pct": avg_buy_future,
        "avg_score": avg_score,
    }


def build_policy(summary_csv: Path, policy_json: Path, allow_txt: Path) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []

    with summary_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            rows.append(row)

    allow = []
    watch_only = []
    block = []

    for row in rows:
        symbol = str(row.get("symbol") or "").upper().strip()
        status = str(row.get("status") or "").lower().strip()

        if not symbol or status != "success":
            continue

        records = safe_int(row.get("records"), 0)
        buy_candidates = safe_int(row.get("buy_candidates"), 0)
        buy_win_rate = safe_float(row.get("buy_candidate_win_rate_pct"), 0.0)
        watch_or_buy_win_rate = safe_float(row.get("watch_or_buy_win_rate_pct"), 0.0)
        avg_future = safe_float(row.get("avg_future_20d_return_pct"), 0.0)
        avg_buy_future = safe_float(row.get("avg_buy_future_20d_return_pct"), 0.0)
        avg_score = safe_float(row.get("avg_score"), 0.0)

        item = {
            "symbol": symbol,
            "records": records,
            "buy_candidates": buy_candidates,
            "buy_candidate_win_rate_pct": buy_win_rate,
            "watch_or_buy_win_rate_pct": watch_or_buy_win_rate,
            "avg_future_20d_return_pct": avg_future,
            "avg_buy_future_20d_return_pct": avg_buy_future,
            "avg_score": avg_score,
        }

        # Conservative policy:
        # Allow only symbols where the actual BUY calls worked historically.
        if buy_candidates >= 10 and buy_win_rate >= 58.0 and avg_buy_future > 0.0:
            item["policy"] = "ALLOW_BUY"
            allow.append(item)

        elif watch_or_buy_win_rate >= 56.0 and avg_future > 0.0:
            item["policy"] = "WATCH_ONLY"
            watch_only.append(item)

        else:
            item["policy"] = "BLOCK_BUY"
            block.append(item)

    allow.sort(
        key=lambda x: (
            x["buy_candidate_win_rate_pct"],
            x["avg_buy_future_20d_return_pct"],
            x["buy_candidates"],
        ),
        reverse=True,
    )

    watch_only.sort(
        key=lambda x: (
            x["watch_or_buy_win_rate_pct"],
            x["avg_future_20d_return_pct"],
        ),
        reverse=True,
    )

    block.sort(
        key=lambda x: (
            x["avg_buy_future_20d_return_pct"],
            x["buy_candidate_win_rate_pct"],
        )
    )

    policy = {
        "build": "ALIENTAI_V2_PREDICTION_20DAY_DAILY_SYMBOL_POLICY_V1",
        "source": str(summary_csv),
        "created_at": now_iso(),
        "rules": {
            "allow_buy": "buy_candidates >= 10 and buy_candidate_win_rate_pct >= 58 and avg_buy_future_20d_return_pct > 0",
            "watch_only": "watch_or_buy_win_rate_pct >= 56 and avg_future_20d_return_pct > 0, unless already allow",
            "block_buy": "everything else",
        },
        "counts": {
            "allow_buy": len(allow),
            "watch_only": len(watch_only),
            "block_buy": len(block),
        },
        "allow_buy": allow,
        "watch_only": watch_only,
        "block_buy": block,
        "allow_symbols": [x["symbol"] for x in allow],
        "watch_only_symbols": [x["symbol"] for x in watch_only],
        "block_symbols": [x["symbol"] for x in block],
    }

    policy_json.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    allow_txt.write_text("\n".join(policy["allow_symbols"]) + "\n", encoding="utf-8")

    return policy


def main() -> None:
    parser = argparse.ArgumentParser(description="Train V2 20-day prediction engine from Supabase daily candles.")
    parser.add_argument("--table", default=DEFAULT_TABLE)
    parser.add_argument("--symbols-file", default="")
    parser.add_argument("--only-symbol", default="")
    parser.add_argument("--limit-symbols", type=int, default=0)
    parser.add_argument("--candle-limit", type=int, default=10000)
    parser.add_argument("--min-history-days", type=int, default=220)
    parser.add_argument("--horizon-days", type=int, default=20)
    parser.add_argument("--step-days", type=int, default=5)
    parser.add_argument("--max-windows-per-symbol", type=int, default=1000)
    parser.add_argument("--buy-score", type=float, default=55.0)
    parser.add_argument("--watch-score", type=float, default=40.0)
    parser.add_argument("--delay", type=float, default=0.1)
    args = parser.parse_args()

    load_env_file(ENV_PATH)

    supabase_url = env_value("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = env_value("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY")

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL missing from .env.")

    if not supabase_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing from .env.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records_path = OUT_DIR / "prediction_20day_daily_records.jsonl"
    summary_csv = OUT_DIR / "prediction_20day_daily_summary.csv"
    summary_json = OUT_DIR / "prediction_20day_daily_summary.json"
    policy_json = OUT_DIR / "prediction_20day_symbol_policy.json"
    allow_txt = OUT_DIR / "prediction_20day_allow_symbols.txt"

    if records_path.exists():
        records_path.unlink()

    if args.only_symbol:
        symbols = [args.only_symbol.upper().strip()]
    elif args.symbols_file:
        symbols = read_symbols_file(Path(args.symbols_file))

        if args.limit_symbols and args.limit_symbols > 0:
            symbols = symbols[:args.limit_symbols]
    else:
        symbols = fetch_symbols_from_daily_table(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            table=args.table,
            limit=args.limit_symbols,
        )

    print(f"Build: {BUILD}")
    print(f"Table: {args.table}")
    print(f"Symbols: {len(symbols)}")
    print(f"Output dir: {OUT_DIR}")
    print(f"Candle limit per symbol: {args.candle_limit}")
    print(f"Min history days: {args.min_history_days}")
    print(f"Horizon days: {args.horizon_days}")
    print(f"Step days: {args.step_days}")
    print(f"Max windows per symbol: {args.max_windows_per_symbol}")
    print("This does NOT touch the V2 paper account.")
    print("")

    summaries: List[Dict[str, Any]] = []

    for index, symbol in enumerate(symbols, start=1):
        print(f"[{index}/{len(symbols)}] Fetching/training {symbol}...")

        try:
            candles = fetch_daily_candles(
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                table=args.table,
                symbol=symbol,
                limit=args.candle_limit,
            )

            summary = train_symbol(
                symbol=symbol,
                candles=candles,
                records_path=records_path,
                min_history_days=args.min_history_days,
                horizon_days=args.horizon_days,
                step_days=args.step_days,
                max_windows_per_symbol=args.max_windows_per_symbol,
                buy_score=args.buy_score,
                watch_score=args.watch_score,
            )

        except Exception as exc:
            summary = {
                "symbol": symbol,
                "status": "error",
                "candles": 0,
                "records": 0,
                "buy_candidates": 0,
                "watch": 0,
                "avoid": 0,
                "buy_candidate_win_rate_pct": "",
                "watch_or_buy_win_rate_pct": "",
                "avg_future_20d_return_pct": "",
                "avg_buy_future_20d_return_pct": "",
                "avg_score": "",
                "error": str(exc),
            }

        summaries.append(summary)

        print(
            f"  {summary.get('status')} | "
            f"candles={summary.get('candles')} "
            f"records={summary.get('records')} "
            f"buy={summary.get('buy_candidates')} "
            f"watch={summary.get('watch')} "
            f"avoid={summary.get('avoid')} "
            f"buy_win={summary.get('buy_candidate_win_rate_pct')} "
            f"avg_buy_forward={summary.get('avg_buy_future_20d_return_pct')} "
            f"avg_score={summary.get('avg_score')}"
        )

        if args.delay > 0:
            time.sleep(args.delay)

    write_csv(summary_csv, summaries)

    success_symbols = sum(1 for s in summaries if s.get("status") == "success")
    total_records = sum(safe_int(s.get("records"), 0) for s in summaries)
    total_buy = sum(safe_int(s.get("buy_candidates"), 0) for s in summaries)
    total_watch = sum(safe_int(s.get("watch"), 0) for s in summaries)
    total_avoid = sum(safe_int(s.get("avoid"), 0) for s in summaries)

    policy = build_policy(summary_csv, policy_json, allow_txt)

    final_summary = {
        "status": "complete",
        "finished_at": now_iso(),
        "build": BUILD,
        "table": args.table,
        "symbols_seen": len(symbols),
        "success_symbols": success_symbols,
        "total_records": total_records,
        "total_buy_candidates": total_buy,
        "total_watch": total_watch,
        "total_avoid": total_avoid,
        "records_path": str(records_path),
        "summary_csv": str(summary_csv),
        "summary_json": str(summary_json),
        "policy_path": str(policy_json),
        "policy_counts": policy.get("counts", {}),
        "settings": {
            "candle_limit": args.candle_limit,
            "min_history_days": args.min_history_days,
            "horizon_days": args.horizon_days,
            "step_days": args.step_days,
            "max_windows_per_symbol": args.max_windows_per_symbol,
            "buy_score": args.buy_score,
            "watch_score": args.watch_score,
        },
    }

    summary_json.write_text(json.dumps(final_summary, indent=2), encoding="utf-8")

    print("")
    print("DONE")
    print(json.dumps(final_summary, indent=2))

    print("")
    print("Top allow symbols:")
    for item in policy.get("allow_buy", [])[:50]:
        print(item)

    print("")
    print("Top watch-only symbols:")
    for item in policy.get("watch_only", [])[:50]:
        print(item)


if __name__ == "__main__":
    main()
