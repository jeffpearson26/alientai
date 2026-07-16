from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from alientai_v2.features.pattern_features import (
    build_pattern_features,
    feature_distance,
    forward_outcome,
    safe_float,
    summarize_similar_outcomes,
)
from alientai_v2.engines.similarity_engine import historical_similarity_score


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data_v2" / "russell_2000_5m_schwab_max"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data_v2" / "similarity_replay_training"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def read_candle_csv(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for raw in reader:
            symbol = str(raw.get("symbol") or "").upper().strip()
            datetime_ms = safe_int(raw.get("datetime_ms"), 0)

            if not symbol or datetime_ms <= 0:
                continue

            rows.append({
                "symbol": symbol,
                "datetime_ms": datetime_ms,
                "datetime_utc": str(raw.get("datetime_utc") or ""),
                "open": safe_float(raw.get("open"), 0.0),
                "high": safe_float(raw.get("high"), 0.0),
                "low": safe_float(raw.get("low"), 0.0),
                "close": safe_float(raw.get("close"), 0.0),
                "volume": safe_float(raw.get("volume"), 0.0),
            })

    rows.sort(key=lambda r: int(r.get("datetime_ms") or 0))
    return rows


def symbol_from_file(path: Path) -> str:
    name = path.name
    return name.replace("_schwab_5m_max.csv", "").upper()


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
    """
    Walk-forward safe similarity search.

    Important:
    It only searches patterns that occurred BEFORE current_index.
    It does not use future candles to make the prediction.

    We also require each prior case to have enough forward candles
    available inside the already-known historical section at that point.
    """

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
    """
    Measures whether the future would have been useful as a trade.

    This is not perfect bar-by-bar stop order simulation yet.
    It asks:
      - Did the future ever reach profit target?
      - Did the future draw down past stop loss?
      - Was final return positive?
    """

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
    file_path: Path,
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
    symbol = symbol_from_file(file_path)
    candles = read_candle_csv(file_path)

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
        # Spread samples across the symbol history rather than only using the earliest section.
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
            "build": "ALIENTAI_V2_SIMILARITY_LOCAL_WALK_FORWARD_V1",
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Train/test V2 similarity engine from local 5-minute CSV files.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--limit-files", type=int, default=0)
    parser.add_argument("--window-bars", type=int, default=12)
    parser.add_argument("--horizon-bars", type=int, default=78)
    parser.add_argument("--min-history-bars", type=int, default=1000)
    parser.add_argument("--step-bars", type=int, default=78)
    parser.add_argument("--max-cases-to-scan", type=int, default=2500)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--max-windows-per-symbol", type=int, default=250)
    parser.add_argument("--similarity-watch-score", type=float, default=45.0)
    parser.add_argument("--similarity-buy-score", type=float, default=62.0)
    parser.add_argument("--profit-target-pct", type=float, default=1.0)
    parser.add_argument("--stop-loss-pct", type=float, default=-1.5)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    output_jsonl = out_dir / "similarity_walk_forward_records.jsonl"
    summary_csv = out_dir / "similarity_walk_forward_summary.csv"
    summary_json = out_dir / "similarity_walk_forward_summary.json"

    if output_jsonl.exists():
        output_jsonl.unlink()

    files = sorted(input_dir.glob("*_schwab_5m_max.csv"))

    if args.limit_files and args.limit_files > 0:
        files = files[:args.limit_files]

    settings = {
        "similarity_watch_score": args.similarity_watch_score,
        "similarity_buy_score": args.similarity_buy_score,
    }

    print("Build: ALIENTAI_V2_SIMILARITY_LOCAL_WALK_FORWARD_TRAINER_V1")
    print(f"Input dir: {input_dir}")
    print(f"Files: {len(files)}")
    print(f"Output dir: {out_dir}")
    print(f"Window bars: {args.window_bars}")
    print(f"Horizon bars: {args.horizon_bars}")
    print(f"Min history bars: {args.min_history_bars}")
    print(f"Step bars: {args.step_bars}")
    print(f"Top K similar cases: {args.top_k}")
    print(f"Max windows per symbol: {args.max_windows_per_symbol}")
    print("This does NOT touch the V2 paper account.")
    print("")

    summaries: List[Dict[str, Any]] = []

    for index, file_path in enumerate(files, start=1):
        symbol = symbol_from_file(file_path)
        print(f"[{index}/{len(files)}] Training {symbol}...")

        try:
            summary = train_symbol(
                file_path=file_path,
                output_jsonl=output_jsonl,
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
            f"records={summary.get('records')} "
            f"buy={summary.get('buy_candidates')} "
            f"watch={summary.get('watch')} "
            f"avoid={summary.get('avoid')} "
            f"win={summary.get('prediction_win_rate_pct')} "
            f"avg_forward={summary.get('avg_forward_return_pct')}"
        )

    write_csv(summary_csv, summaries)

    total_records = sum(safe_int(s.get("records"), 0) for s in summaries)
    total_buy = sum(safe_int(s.get("buy_candidates"), 0) for s in summaries)
    total_watch = sum(safe_int(s.get("watch"), 0) for s in summaries)
    total_avoid = sum(safe_int(s.get("avoid"), 0) for s in summaries)
    success_symbols = sum(1 for s in summaries if s.get("status") == "success")

    final_summary = {
        "status": "complete",
        "finished_at": now_iso(),
        "build": "ALIENTAI_V2_SIMILARITY_LOCAL_WALK_FORWARD_TRAINER_V1",
        "input_dir": str(input_dir),
        "files_seen": len(files),
        "success_symbols": success_symbols,
        "total_records": total_records,
        "total_buy_candidates": total_buy,
        "total_watch": total_watch,
        "total_avoid": total_avoid,
        "records_path": str(output_jsonl),
        "summary_csv": str(summary_csv),
        "window_bars": args.window_bars,
        "horizon_bars": args.horizon_bars,
        "min_history_bars": args.min_history_bars,
        "step_bars": args.step_bars,
        "max_cases_to_scan": args.max_cases_to_scan,
        "top_k": args.top_k,
        "max_windows_per_symbol": args.max_windows_per_symbol,
    }

    summary_json.write_text(json.dumps(final_summary, indent=2), encoding="utf-8")

    print("")
    print("DONE")
    print(json.dumps(final_summary, indent=2))

    print("")
    print("Top symbols by buy_candidate_win_rate_pct:")
    ranked = [
        s for s in summaries
        if s.get("buy_candidate_win_rate_pct") not in ("", None)
        and safe_int(s.get("buy_candidates"), 0) >= 3
    ]

    ranked.sort(key=lambda s: float(s.get("buy_candidate_win_rate_pct") or 0), reverse=True)

    for row in ranked[:20]:
        print(row)


if __name__ == "__main__":
    main()
