from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests

from alientai_v2.features.pattern_features import (
    build_pattern_features,
    feature_distance,
    forward_outcome,
    safe_float,
    summarize_similar_outcomes,
)
from alientai_v2.engines.similarity_engine import historical_similarity_score


PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"

OUT_DIR = PROJECT_ROOT / "data_v2" / "similarity_supabase_replay_training"
DEFAULT_TABLE = "v2_5min_candles"
DEFAULT_LOCAL_HISTORY_DIR = PROJECT_ROOT / "data_v2" / "russell_2000_5m_schwab_max"


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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
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
        raise RuntimeError(f"Supabase HTTP {response.status_code}: {response.text[:500]}")

    return response.json()


def fetch_symbols_from_supabase(
    *,
    supabase_url: str,
    supabase_key: str,
    table: str,
    limit: int,
) -> List[str]:
    """
    Simple symbol discovery.

    This uses rows from the table and deduplicates symbols locally.
    For a huge table, this is not perfect, but it is good enough for the
    current 247-symbol batch.
    """
    rows = supabase_get(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        table=table,
        params={
            "select": "symbol",
            "order": "symbol.asc",
            "limit": "200000",
        },
    )

    symbols = sorted(set(str(r.get("symbol") or "").upper().strip() for r in rows if r.get("symbol")))

    if limit and limit > 0:
        symbols = symbols[:limit]

    return symbols


def fetch_symbol_candles_from_supabase(
    *,
    supabase_url: str,
    supabase_key: str,
    table: str,
    symbol: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Fetches candles in pages.

    Supabase/PostgREST commonly returns only around 1000 rows per request,
    even if a bigger limit is requested. So we page through the result set
    using datetime_ms cursor logic.

    We fetch newest-to-oldest, then sort oldest-to-newest before replay.
    """
    symbol = str(symbol or "").upper().strip()

    all_rows: List[Dict[str, Any]] = []
    page_size = 1000
    before_ms = None

    while len(all_rows) < limit:
        remaining = limit - len(all_rows)
        this_limit = min(page_size, remaining)

        params = {
            "select": "symbol,datetime_ms,datetime_utc,open,high,low,close,volume",
            "symbol": f"eq.{symbol}",
            "timeframe": "eq.5m",
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

        time.sleep(0.05)

    candles: List[Dict[str, Any]] = []

    seen = set()

    for raw in all_rows:
        datetime_ms = safe_int(raw.get("datetime_ms"), 0)

        if datetime_ms <= 0:
            continue

        dedupe_key = (symbol, datetime_ms)

        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)

        candles.append({
            "symbol": str(raw.get("symbol") or symbol).upper().strip(),
            "datetime_ms": datetime_ms,
            "datetime_utc": str(raw.get("datetime_utc") or ""),
            "open": safe_float(raw.get("open"), 0.0),
            "high": safe_float(raw.get("high"), 0.0),
            "low": safe_float(raw.get("low"), 0.0),
            "close": safe_float(raw.get("close"), 0.0),
            "volume": safe_float(raw.get("volume"), 0.0),
        })

    candles.sort(key=lambda r: int(r.get("datetime_ms") or 0))
    return candles


def find_similar_prior_cases(
    candles: List[Dict[str, Any]],
    current_index: int,
    current_features: Dict[str, float],
    *,
    window_bars: int,
    horizon_bars: int,
    max_cases_to_scan: int,
    top_k: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, float]]]:
    earliest_index = window_bars
    latest_prior_index = current_index - horizon_bars - 1

    if latest_prior_index <= earliest_index:
        return [], []

    prior_indices = list(range(earliest_index, latest_prior_index))

    if max_cases_to_scan > 0 and len(prior_indices) > max_cases_to_scan:
        prior_indices = prior_indices[-max_cases_to_scan:]

    scored: List[Tuple[float, int, Dict[str, float]]] = []

    for idx in prior_indices:
        past_slice = candles[:idx + 1]
        past_features = build_pattern_features(past_slice, window=window_bars)

        if not past_features:
            continue

        distance = feature_distance(current_features, past_features)
        scored.append((distance, idx, past_features))

    scored.sort(key=lambda x: x[0])

    similar_cases: List[Dict[str, Any]] = []
    outcomes: List[Dict[str, float]] = []

    for distance, idx, past_features in scored[:top_k]:
        outcome = forward_outcome(candles, idx, horizon_bars=horizon_bars)

        if not outcome:
            continue

        similar_cases.append({
            "distance": round(distance, 6),
            "index": idx,
            "datetime_utc": candles[idx].get("datetime_utc"),
            "features": past_features,
            "outcome": outcome,
        })

        outcomes.append(outcome)

    return similar_cases, outcomes


def classify_prediction(score: float, settings: Dict[str, Any]) -> str:
    buy_score = safe_float(settings.get("similarity_buy_score"), 62.0)
    watch_score = safe_float(settings.get("similarity_watch_score"), 45.0)

    if score >= buy_score:
        return "BUY_CANDIDATE"

    if score >= watch_score:
        return "WATCH"

    return "AVOID"


def score_actual_trade(outcome: Dict[str, float], *, profit_target_pct: float, stop_loss_pct: float) -> Dict[str, Any]:
    forward_return = safe_float(outcome.get("forward_return_pct"), 0.0)
    max_gain = safe_float(outcome.get("max_gain_pct"), 0.0)
    max_drawdown = safe_float(outcome.get("max_drawdown_pct"), 0.0)

    hit_profit_target = max_gain >= profit_target_pct
    hit_stop_zone = max_drawdown <= stop_loss_pct
    final_up = forward_return > 0

    useful_trade = bool(hit_profit_target and not hit_stop_zone)

    return {
        "final_up": final_up,
        "hit_profit_target": hit_profit_target,
        "hit_stop_zone": hit_stop_zone,
        "useful_trade": useful_trade,
    }


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
    output_jsonl: Path,
    window_bars: int,
    horizon_bars: int,
    min_history_bars: int,
    step_bars: int,
    max_cases_to_scan: int,
    top_k: int,
    max_windows_per_symbol: int,
    settings: Dict[str, Any],
    profit_target_pct: float,
    stop_loss_pct: float,
) -> Dict[str, Any]:
    if len(candles) < min_history_bars + horizon_bars + window_bars:
        return {
            "symbol": symbol,
            "status": "too_few_candles",
            "candles": len(candles),
            "records": 0,
            "buy_candidates": 0,
            "watch": 0,
            "avoid": 0,
            "prediction_win_rate_pct": "",
            "buy_candidate_win_rate_pct": "",
            "avg_forward_return_pct": "",
            "avg_score": "",
        }

    records = 0
    buy_candidates = 0
    watch = 0
    avoid = 0

    predicted_direction_count = 0
    predicted_direction_wins = 0

    buy_candidate_count = 0
    buy_candidate_wins = 0

    forward_returns: List[float] = []
    scores: List[float] = []

    start_index = min_history_bars
    end_index = len(candles) - horizon_bars - 1

    indices = list(range(start_index, end_index, step_bars))

    if max_windows_per_symbol > 0 and len(indices) > max_windows_per_symbol:
        stride = max(1, math.floor(len(indices) / max_windows_per_symbol))
        indices = indices[::stride][:max_windows_per_symbol]

    for current_index in indices:
        past_slice = candles[:current_index + 1]
        current_features = build_pattern_features(past_slice, window=window_bars)

        if not current_features:
            continue

        similar_cases, similar_outcomes = find_similar_prior_cases(
            candles,
            current_index,
            current_features,
            window_bars=window_bars,
            horizon_bars=horizon_bars,
            max_cases_to_scan=max_cases_to_scan,
            top_k=top_k,
        )

        summary = summarize_similar_outcomes(similar_outcomes)

        if int(summary.get("cases", 0)) <= 0:
            continue

        score = historical_similarity_score(summary, settings)
        decision = classify_prediction(score, settings)

        actual_outcome = forward_outcome(candles, current_index, horizon_bars=horizon_bars)

        if not actual_outcome:
            continue

        trade_score = score_actual_trade(
            actual_outcome,
            profit_target_pct=profit_target_pct,
            stop_loss_pct=stop_loss_pct,
        )

        actual_forward_return = safe_float(actual_outcome.get("forward_return_pct"), 0.0)
        actual_final_up = bool(trade_score["final_up"])

        if decision == "BUY_CANDIDATE":
            buy_candidates += 1
            buy_candidate_count += 1

            if actual_final_up:
                buy_candidate_wins += 1

        elif decision == "WATCH":
            watch += 1
        else:
            avoid += 1

        if decision in {"BUY_CANDIDATE", "WATCH"}:
            predicted_direction_count += 1

            if actual_final_up:
                predicted_direction_wins += 1

        forward_returns.append(actual_forward_return)
        scores.append(score)

        record = {
            "build": "ALIENTAI_V2_SIMILARITY_SUPABASE_WALK_FORWARD_V1",
            "symbol": symbol,
            "prediction_time_utc": candles[current_index].get("datetime_utc"),
            "prediction_datetime_ms": candles[current_index].get("datetime_ms"),
            "window_bars": window_bars,
            "horizon_bars": horizon_bars,
            "lookback_candles_available": current_index + 1,
            "decision": decision,
            "score": score,
            "current_features": current_features,
            "similar_summary": summary,
            "similar_cases_used": int(summary.get("cases", 0)),
            "actual_forward_return_pct": actual_forward_return,
            "actual_max_gain_pct": safe_float(actual_outcome.get("max_gain_pct"), 0.0),
            "actual_max_drawdown_pct": safe_float(actual_outcome.get("max_drawdown_pct"), 0.0),
            "actual_final_up": actual_final_up,
            "actual_hit_profit_target": bool(trade_score["hit_profit_target"]),
            "actual_hit_stop_zone": bool(trade_score["hit_stop_zone"]),
            "actual_useful_trade": bool(trade_score["useful_trade"]),
            "history_source": "supabase",
        }

        append_jsonl(output_jsonl, record)
        records += 1

    prediction_win_rate = ""
    if predicted_direction_count > 0:
        prediction_win_rate = round((predicted_direction_wins / predicted_direction_count) * 100.0, 2)

    buy_win_rate = ""
    if buy_candidate_count > 0:
        buy_win_rate = round((buy_candidate_wins / buy_candidate_count) * 100.0, 2)

    avg_forward = ""
    if forward_returns:
        avg_forward = round(sum(forward_returns) / len(forward_returns), 4)

    avg_score = ""
    if scores:
        avg_score = round(sum(scores) / len(scores), 4)

    return {
        "symbol": symbol,
        "status": "success",
        "candles": len(candles),
        "records": records,
        "buy_candidates": buy_candidates,
        "watch": watch,
        "avoid": avoid,
        "prediction_win_rate_pct": prediction_win_rate,
        "buy_candidate_win_rate_pct": buy_win_rate,
        "avg_forward_return_pct": avg_forward,
        "avg_score": avg_score,
    }


def build_policy(summary_csv: Path, out_json: Path, out_txt: Path) -> Dict[str, Any]:
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

        records = safe_int(row.get("records"))
        buy_candidates = safe_int(row.get("buy_candidates"))
        prediction_win_rate = safe_float(row.get("prediction_win_rate_pct"), 0.0)
        buy_win_rate = safe_float(row.get("buy_candidate_win_rate_pct"), 0.0)
        avg_forward = safe_float(row.get("avg_forward_return_pct"), 0.0)
        avg_score = safe_float(row.get("avg_score"), 0.0)

        item = {
            "symbol": symbol,
            "records": records,
            "buy_candidates": buy_candidates,
            "prediction_win_rate_pct": prediction_win_rate,
            "buy_candidate_win_rate_pct": buy_win_rate,
            "avg_forward_return_pct": avg_forward,
            "avg_score": avg_score,
        }

        if buy_candidates >= 10 and buy_win_rate >= 60.0 and avg_forward > 0:
            item["policy"] = "ALLOW_BUY"
            allow.append(item)
        elif prediction_win_rate >= 58.0 and avg_forward > 0:
            item["policy"] = "WATCH_ONLY"
            watch_only.append(item)
        else:
            item["policy"] = "BLOCK_BUY"
            block.append(item)

    allow.sort(key=lambda x: (x["buy_candidate_win_rate_pct"], x["avg_forward_return_pct"], x["buy_candidates"]), reverse=True)
    watch_only.sort(key=lambda x: (x["prediction_win_rate_pct"], x["avg_forward_return_pct"]), reverse=True)
    block.sort(key=lambda x: (x["avg_forward_return_pct"], x["buy_candidate_win_rate_pct"]))

    policy = {
        "build": "ALIENTAI_V2_SIMILARITY_SUPABASE_SYMBOL_POLICY_V1",
        "source": str(summary_csv),
        "created_at": now_iso(),
        "rules": {
            "allow_buy": "buy_candidates >= 10 and buy_candidate_win_rate_pct >= 60 and avg_forward_return_pct > 0",
            "watch_only": "prediction_win_rate_pct >= 58 and avg_forward_return_pct > 0, unless already allow",
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

    out_json.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    out_txt.write_text("\n".join(policy["allow_symbols"]) + "\n", encoding="utf-8")

    return policy



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


def symbols_from_local_history_folder(path: Path, limit: int = 0) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Local history folder not found: {path}")

    symbols = []

    for file_path in sorted(path.glob("*_schwab_5m_max.csv")):
        symbol = file_path.name.replace("_schwab_5m_max.csv", "").upper().strip()

        if symbol:
            symbols.append(symbol)

    symbols = sorted(set(symbols))

    if limit and limit > 0:
        symbols = symbols[:limit]

    return symbols

def main() -> None:
    parser = argparse.ArgumentParser(description="Train/test V2 similarity engine from Supabase 5-minute candles.")
    parser.add_argument("--table", default=DEFAULT_TABLE)
    parser.add_argument("--symbols-file", default="")
    parser.add_argument("--symbols-from-local-folder", action="store_true")
    parser.add_argument("--local-history-dir", default=str(DEFAULT_LOCAL_HISTORY_DIR))
    parser.add_argument("--limit-symbols", type=int, default=0)
    parser.add_argument("--only-symbol", default="")
    parser.add_argument("--candle-limit", type=int, default=50000)
    parser.add_argument("--window-bars", type=int, default=12)
    parser.add_argument("--horizon-bars", type=int, default=78)
    parser.add_argument("--min-history-bars", type=int, default=1000)
    parser.add_argument("--step-bars", type=int, default=78)
    parser.add_argument("--max-cases-to-scan", type=int, default=2500)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--max-windows-per-symbol", type=int, default=150)
    parser.add_argument("--similarity-watch-score", type=float, default=45.0)
    parser.add_argument("--similarity-buy-score", type=float, default=62.0)
    parser.add_argument("--profit-target-pct", type=float, default=1.0)
    parser.add_argument("--stop-loss-pct", type=float, default=-1.5)
    parser.add_argument("--delay", type=float, default=0.2)
    args = parser.parse_args()

    load_env_file(ENV_PATH)

    supabase_url = env_value("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = env_value("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY")

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL missing from .env.")

    if not supabase_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing from .env.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records_jsonl = OUT_DIR / "similarity_supabase_walk_forward_records.jsonl"
    summary_csv = OUT_DIR / "similarity_supabase_walk_forward_summary.csv"
    summary_json = OUT_DIR / "similarity_supabase_walk_forward_summary.json"
    policy_json = OUT_DIR / "similarity_symbol_policy.json"
    allow_txt = OUT_DIR / "similarity_allow_symbols.txt"

    if records_jsonl.exists():
        records_jsonl.unlink()

    if args.only_symbol:
        symbols = [args.only_symbol.upper().strip()]
    elif args.symbols_file:
        symbols = read_symbols_file(Path(args.symbols_file))

        if args.limit_symbols and args.limit_symbols > 0:
            symbols = symbols[:args.limit_symbols]
    elif args.symbols_from_local_folder:
        symbols = symbols_from_local_history_folder(Path(args.local_history_dir), limit=args.limit_symbols)
    else:
        symbols = fetch_symbols_from_supabase(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            table=args.table,
            limit=args.limit_symbols,
        )

    settings = {
        "similarity_watch_score": args.similarity_watch_score,
        "similarity_buy_score": args.similarity_buy_score,
    }

    print("Build: ALIENTAI_V2_SIMILARITY_SUPABASE_WALK_FORWARD_TRAINER_V1")
    print(f"Table: {args.table}")
    print(f"Symbols: {len(symbols)}")
    print(f"Output dir: {OUT_DIR}")
    print(f"Candle limit per symbol: {args.candle_limit}")
    print(f"Max windows per symbol: {args.max_windows_per_symbol}")
    print("This does NOT touch the V2 paper account.")
    print("")

    summaries: List[Dict[str, Any]] = []

    for index, symbol in enumerate(symbols, start=1):
        print(f"[{index}/{len(symbols)}] Fetching/training {symbol}...")

        try:
            candles = fetch_symbol_candles_from_supabase(
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                table=args.table,
                symbol=symbol,
                limit=args.candle_limit,
            )

            summary = train_symbol(
                symbol=symbol,
                candles=candles,
                output_jsonl=records_jsonl,
                window_bars=args.window_bars,
                horizon_bars=args.horizon_bars,
                min_history_bars=args.min_history_bars,
                step_bars=args.step_bars,
                max_cases_to_scan=args.max_cases_to_scan,
                top_k=args.top_k,
                max_windows_per_symbol=args.max_windows_per_symbol,
                settings=settings,
                profit_target_pct=args.profit_target_pct,
                stop_loss_pct=args.stop_loss_pct,
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
                "prediction_win_rate_pct": "",
                "buy_candidate_win_rate_pct": "",
                "avg_forward_return_pct": "",
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
            f"avg_forward={summary.get('avg_forward_return_pct')}"
        )

        if args.delay > 0:
            time.sleep(args.delay)

    write_csv(summary_csv, summaries)

    total_records = sum(safe_int(s.get("records"), 0) for s in summaries)
    total_buy = sum(safe_int(s.get("buy_candidates"), 0) for s in summaries)
    total_watch = sum(safe_int(s.get("watch"), 0) for s in summaries)
    total_avoid = sum(safe_int(s.get("avoid"), 0) for s in summaries)
    success_symbols = sum(1 for s in summaries if s.get("status") == "success")

    final_summary = {
        "status": "complete",
        "finished_at": now_iso(),
        "build": "ALIENTAI_V2_SIMILARITY_SUPABASE_WALK_FORWARD_TRAINER_V1",
        "table": args.table,
        "symbols_seen": len(symbols),
        "success_symbols": success_symbols,
        "total_records": total_records,
        "total_buy_candidates": total_buy,
        "total_watch": total_watch,
        "total_avoid": total_avoid,
        "records_path": str(records_jsonl),
        "summary_csv": str(summary_csv),
        "summary_json": str(summary_json),
    }

    policy = build_policy(summary_csv, policy_json, allow_txt)
    final_summary["policy_path"] = str(policy_json)
    final_summary["policy_counts"] = policy.get("counts", {})

    summary_json.write_text(json.dumps(final_summary, indent=2), encoding="utf-8")

    print("")
    print("DONE")
    print(json.dumps(final_summary, indent=2))

    print("")
    print("Top allow symbols:")
    for item in policy.get("allow_buy", [])[:40]:
        print(item)


if __name__ == "__main__":
    main()


