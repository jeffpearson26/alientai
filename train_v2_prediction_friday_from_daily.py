from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


BUILD = "ALIENTAI_V2_PREDICTION_FRIDAY_DAILY_TRAINER_V1"

PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_ROOT / "data_v2" / "daily_schwab_max_history"
OUT_DIR = PROJECT_ROOT / "data_v2" / "prediction_friday_daily_training"

RECORDS_PATH = OUT_DIR / "prediction_friday_daily_records.jsonl"
SUMMARY_CSV = OUT_DIR / "prediction_friday_daily_summary.csv"
SUMMARY_JSON = OUT_DIR / "prediction_friday_daily_summary.json"
POLICY_PATH = OUT_DIR / "prediction_friday_symbol_policy.json"
ALLOW_SYMBOLS_PATH = OUT_DIR / "prediction_friday_allow_symbols.txt"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def parse_date(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None

    # Common forms from CSV/history files.
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text[:19], fmt)
        except Exception:
            pass

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def normalize_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    lower = {str(k).strip().lower(): v for k, v in row.items()}

    date_value = (
        lower.get("date")
        or lower.get("datetime")
        or lower.get("time")
        or lower.get("timestamp")
        or lower.get("day")
    )

    dt = parse_date(date_value)
    if not dt:
        return None

    close = safe_float(lower.get("close") or lower.get("c"), 0.0)
    open_ = safe_float(lower.get("open") or lower.get("o"), close)
    high = safe_float(lower.get("high") or lower.get("h"), close)
    low = safe_float(lower.get("low") or lower.get("l"), close)
    volume = safe_float(lower.get("volume") or lower.get("v"), 0.0)

    if close <= 0:
        return None

    return {
        "date": dt.date().isoformat(),
        "dt": dt,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


def load_symbol_file(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = normalize_row(raw)
            if row:
                rows.append(row)

    rows.sort(key=lambda r: r["dt"])
    return rows


def symbol_from_file(path: Path) -> str:
    """
    Extract ticker from your Schwab daily filenames.

    Your files look like:
      MARA_schwab_1d_max.csv
      AAPL_schwab_1d_max.csv

    So the ticker is the part before the first underscore.
    """
    stem = path.stem.upper().strip()
    if "_" in stem:
        return stem.split("_", 1)[0].strip()
    return stem


def load_symbols_from_file(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(path)

    symbols = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip().upper()
        if s and not s.startswith("#"):
            symbols.append(s)

    return list(dict.fromkeys(symbols))


def week_key(dt: datetime) -> str:
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


def build_week_end_map(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    For each ISO week, use the final trading day of that week.
    Usually Friday. If Friday is a holiday, this uses Thursday.
    """
    by_week: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for row in rows:
        by_week[week_key(row["dt"])].append(row)

    week_end = {}

    for key, items in by_week.items():
        items.sort(key=lambda r: r["dt"])
        week_end[key] = items[-1]

    return week_end


def pct_change(a: float, b: float) -> float:
    if a <= 0:
        return 0.0
    return ((b - a) / a) * 100.0


def moving_avg(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def score_entry(row: Dict[str, Any], history: List[Dict[str, Any]]) -> float:
    """
    Simple transparent score.
    Later we can replace this with ML, transformer, or LightGBM.
    """
    close = safe_float(row["close"], 0.0)
    if close <= 0:
        return 0.0

    closes = [safe_float(r["close"], 0.0) for r in history if safe_float(r["close"], 0.0) > 0]
    volumes = [safe_float(r["volume"], 0.0) for r in history]

    if len(closes) < 30:
        return 0.0

    ret_1 = pct_change(closes[-2], closes[-1]) if len(closes) >= 2 else 0.0
    ret_5 = pct_change(closes[-6], closes[-1]) if len(closes) >= 6 else 0.0
    ret_10 = pct_change(closes[-11], closes[-1]) if len(closes) >= 11 else 0.0
    ret_20 = pct_change(closes[-21], closes[-1]) if len(closes) >= 21 else 0.0

    ma_5 = moving_avg(closes[-5:])
    ma_10 = moving_avg(closes[-10:])
    ma_20 = moving_avg(closes[-20:])
    ma_50 = moving_avg(closes[-50:]) if len(closes) >= 50 else moving_avg(closes)

    vol_now = volumes[-1] if volumes else 0.0
    vol_avg_20 = moving_avg(volumes[-20:]) if len(volumes) >= 20 else moving_avg(volumes)
    rel_vol = vol_now / vol_avg_20 if vol_avg_20 > 0 else 1.0

    score = 0.0

    # Momentum into Friday.
    if ret_1 > 0:
        score += 8
    if ret_5 > 1:
        score += 12
    if ret_10 > 2:
        score += 10
    if ret_20 > 3:
        score += 8

    # Trend structure.
    if close > ma_5:
        score += 8
    if close > ma_10:
        score += 8
    if close > ma_20:
        score += 8
    if close > ma_50:
        score += 6
    if ma_5 > ma_10 > ma_20:
        score += 10

    # Volume confirmation.
    if rel_vol >= 1.2:
        score += 8
    elif rel_vol >= 1.0:
        score += 4

    # Avoid very extended short-term moves.
    if ret_5 > 12:
        score -= 10
    if ret_1 > 8:
        score -= 8

    return round(max(0.0, min(100.0, score)), 4)


def decision_from_score(score: float, buy_score: float, watch_score: float) -> str:
    if score >= buy_score:
        return "BUY_CANDIDATE"
    if score >= watch_score:
        return "WATCH"
    return "AVOID"


def make_records_for_symbol(
    symbol: str,
    rows: List[Dict[str, Any]],
    min_history_days: int,
    max_windows: int,
    buy_score: float,
    watch_score: float,
) -> List[Dict[str, Any]]:
    week_end = build_week_end_map(rows)
    records: List[Dict[str, Any]] = []

    # Keep chronological windows.
    for i in range(min_history_days, len(rows)):
        row = rows[i]
        dt = row["dt"]

        # Friday is weekday 4. For training, skip the last trading day of the week.
        # We only want entries before the weekly target close.
        key = week_key(dt)
        target = week_end.get(key)

        if not target:
            continue

        if target["dt"].date() <= dt.date():
            continue

        entry_close = safe_float(row["close"], 0.0)
        target_close = safe_float(target["close"], 0.0)

        if entry_close <= 0 or target_close <= 0:
            continue

        future_return = pct_change(entry_close, target_close)

        history = rows[: i + 1]
        score = score_entry(row, history)
        decision = decision_from_score(score, buy_score, watch_score)

        win = future_return > 0

        records.append({
            "symbol": symbol,
            "entry_date": row["date"],
            "entry_weekday": dt.strftime("%A"),
            "target_date": target["date"],
            "target_weekday": target["dt"].strftime("%A"),
            "days_to_target": (target["dt"].date() - dt.date()).days,
            "entry_close": round(entry_close, 4),
            "target_close": round(target_close, 4),
            "future_friday_return_pct": round(future_return, 4),
            "win": win,
            "score": score,
            "decision": decision,
        })

    if max_windows > 0 and len(records) > max_windows:
        records = records[-max_windows:]

    return records


def summarize_symbol(symbol: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(records)
    buys = [r for r in records if r["decision"] == "BUY_CANDIDATE"]
    watches = [r for r in records if r["decision"] == "WATCH"]
    avoids = [r for r in records if r["decision"] == "AVOID"]

    def win_rate(items: List[Dict[str, Any]]) -> float:
        if not items:
            return 0.0
        return round(sum(1 for r in items if r["win"]) / len(items) * 100.0, 2)

    def avg_return(items: List[Dict[str, Any]]) -> float:
        if not items:
            return 0.0
        return round(sum(safe_float(r["future_friday_return_pct"], 0.0) for r in items) / len(items), 4)

    buy_win = win_rate(buys)
    avg_buy_return = avg_return(buys)

    # Conservative policy rules.
    if len(buys) >= 60 and buy_win >= 58 and avg_buy_return > 0:
        policy = "ALLOW_BUY_STRONG"
    elif len(buys) >= 30 and buy_win >= 55 and avg_buy_return > 0:
        policy = "ALLOW_BUY"
    elif len(buys) >= 20 and buy_win >= 52 and avg_buy_return > 0:
        policy = "WATCH_ONLY"
    elif total <= 0:
        policy = "NO_DATA"
    else:
        policy = "BLOCK_BUY"

    return {
        "symbol": symbol,
        "status": "success" if total else "no_records",
        "records": total,
        "buy_candidates": len(buys),
        "watch": len(watches),
        "avoid": len(avoids),
        "buy_candidate_win_rate_pct": buy_win,
        "watch_or_buy_win_rate_pct": win_rate(buys + watches),
        "avg_future_friday_return_pct": avg_return(records),
        "avg_buy_future_friday_return_pct": avg_buy_return,
        "avg_score": round(sum(safe_float(r["score"], 0.0) for r in records) / total, 4) if total else 0.0,
        "policy": policy,
    }


def find_symbol_files(symbol_filter: Optional[List[str]]) -> List[Path]:
    """
    Find daily Schwab history files.

    Your downloaded files are named like:
      MARA_schwab_1d_max.csv
      AAPL_schwab_1d_max.csv

    This matcher uses the filename prefix before the first underscore as the ticker.
    """
    files = sorted(INPUT_DIR.rglob("*.csv"))

    if not symbol_filter:
        return files

    wanted = {str(s).upper().strip() for s in symbol_filter if str(s).strip()}
    matched: List[Path] = []

    for p in files:
        stem = p.stem.upper()
        file_ticker = stem.split("_", 1)[0].strip()

        if file_ticker in wanted:
            matched.append(p)

    return matched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-symbol", default="")
    parser.add_argument("--symbols-file", default="")
    parser.add_argument("--min-history-days", type=int, default=160)
    parser.add_argument("--max-windows-per-symbol", type=int, default=1000)
    parser.add_argument("--buy-score", type=float, default=55.0)
    parser.add_argument("--watch-score", type=float, default=40.0)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    symbols = []
    if args.only_symbol:
        symbols = [args.only_symbol.upper().strip()]
    elif args.symbols_file:
        symbols = load_symbols_from_file(Path(args.symbols_file))

    files = find_symbol_files(symbols if symbols else None)

    summaries: List[Dict[str, Any]] = []
    all_records_count = 0

    print(f"Build: {BUILD}")
    print(f"Input dir: {INPUT_DIR}")
    print(f"Output dir: {OUT_DIR}")
    print(f"Symbols/files: {len(files)}")
    print(f"Min history days: {args.min_history_days}")
    print("Target: outcome by same week's final trading day, normally Friday.")
    print("This does NOT touch the V2 paper account.")
    print("")

    with RECORDS_PATH.open("w", encoding="utf-8") as records_file:
        for idx, file_path in enumerate(files, start=1):
            symbol = symbol_from_file(file_path)
            print(f"[{idx}/{len(files)}] Training {symbol}...")

            try:
                rows = load_symbol_file(file_path)
                records = make_records_for_symbol(
                    symbol=symbol,
                    rows=rows,
                    min_history_days=args.min_history_days,
                    max_windows=args.max_windows_per_symbol,
                    buy_score=args.buy_score,
                    watch_score=args.watch_score,
                )

                for rec in records:
                    records_file.write(json.dumps(rec) + "\n")

                summary = summarize_symbol(symbol, records)
                summary["candles"] = len(rows)
                summaries.append(summary)
                all_records_count += len(records)

                print(
                    f"  {summary['status']} | candles={len(rows)} records={summary['records']} "
                    f"buy={summary['buy_candidates']} watch={summary['watch']} avoid={summary['avoid']} "
                    f"buy_win={summary['buy_candidate_win_rate_pct']} "
                    f"avg_buy_forward={summary['avg_buy_future_friday_return_pct']} "
                    f"policy={summary['policy']}"
                )

            except Exception as exc:
                summary = {
                    "symbol": symbol,
                    "status": "error",
                    "error": str(exc),
                    "records": 0,
                    "buy_candidates": 0,
                    "watch": 0,
                    "avoid": 0,
                    "buy_candidate_win_rate_pct": 0.0,
                    "watch_or_buy_win_rate_pct": 0.0,
                    "avg_future_friday_return_pct": 0.0,
                    "avg_buy_future_friday_return_pct": 0.0,
                    "avg_score": 0.0,
                    "policy": "NO_DATA",
                    "candles": 0,
                }
                summaries.append(summary)
                print(f"  ERROR: {exc}")

    fieldnames = [
        "symbol",
        "status",
        "candles",
        "records",
        "buy_candidates",
        "watch",
        "avoid",
        "buy_candidate_win_rate_pct",
        "watch_or_buy_win_rate_pct",
        "avg_future_friday_return_pct",
        "avg_buy_future_friday_return_pct",
        "avg_score",
        "policy",
        "error",
    ]

    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for summary in summaries:
            writer.writerow(summary)

    policy = {s["symbol"]: s for s in summaries}

    POLICY_PATH.write_text(json.dumps(policy, indent=2), encoding="utf-8")

    allow_symbols = [
        s["symbol"]
        for s in summaries
        if s.get("policy") in {"ALLOW_BUY_STRONG", "ALLOW_BUY"}
    ]

    ALLOW_SYMBOLS_PATH.write_text("\n".join(allow_symbols) + "\n", encoding="utf-8")

    policy_counts = defaultdict(int)
    for s in summaries:
        policy_counts[s.get("policy", "UNKNOWN")] += 1

    final = {
        "status": "complete",
        "finished_at": datetime.now().replace(microsecond=0).isoformat(),
        "build": BUILD,
        "symbols_seen": len(summaries),
        "success_symbols": sum(1 for s in summaries if s.get("status") == "success"),
        "total_records": all_records_count,
        "summary_csv": str(SUMMARY_CSV),
        "summary_json": str(SUMMARY_JSON),
        "records_path": str(RECORDS_PATH),
        "policy_path": str(POLICY_PATH),
        "allow_symbols_path": str(ALLOW_SYMBOLS_PATH),
        "policy_counts": dict(policy_counts),
        "settings": {
            "min_history_days": args.min_history_days,
            "max_windows_per_symbol": args.max_windows_per_symbol,
            "buy_score": args.buy_score,
            "watch_score": args.watch_score,
            "target": "same_week_final_trading_day_normally_friday",
        },
    }

    SUMMARY_JSON.write_text(json.dumps(final, indent=2), encoding="utf-8")

    print("")
    print("DONE")
    print(json.dumps(final, indent=2))

    print("")
    print("Top Friday allow symbols:")
    for row in sorted(
        [s for s in summaries if s.get("policy") in {"ALLOW_BUY_STRONG", "ALLOW_BUY"}],
        key=lambda r: safe_float(r.get("buy_candidate_win_rate_pct"), 0.0),
        reverse=True,
    )[:30]:
        print({
            "symbol": row.get("symbol"),
            "policy": row.get("policy"),
            "records": row.get("records"),
            "buy_candidates": row.get("buy_candidates"),
            "buy_win": row.get("buy_candidate_win_rate_pct"),
            "avg_buy_friday_return": row.get("avg_buy_future_friday_return_pct"),
        })


if __name__ == "__main__":
    main()
