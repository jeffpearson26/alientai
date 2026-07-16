from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


BUILD = "ALIENTAI_V2_PREDICTION_20DAY_MASTER_POLICY_BUILDER_V1"

PROJECT_ROOT = Path(__file__).resolve().parent
TRAIN_DIR = PROJECT_ROOT / "data_v2" / "prediction_20day_daily_training"
BATCH_DIR = TRAIN_DIR / "batches"

MASTER_POLICY_PATH = TRAIN_DIR / "prediction_20day_master_symbol_policy.json"
MASTER_SUMMARY_CSV = TRAIN_DIR / "prediction_20day_master_summary.csv"
MASTER_ALLOW_SYMBOLS = TRAIN_DIR / "prediction_20day_master_allow_symbols.txt"
MASTER_STRONG_ALLOW_SYMBOLS = TRAIN_DIR / "prediction_20day_master_strong_allow_symbols.txt"
MASTER_SMALL_ALLOW_SYMBOLS = TRAIN_DIR / "prediction_20day_master_small_allow_symbols.txt"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


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


def classify(row: Dict[str, Any]) -> str:
    status = str(row.get("status", "")).lower()
    records = safe_int(row.get("records"), 0)
    buy_candidates = safe_int(row.get("buy_candidates"), 0)
    buy_win = safe_float(row.get("buy_candidate_win_rate_pct"), 0.0)
    watch_buy_win = safe_float(row.get("watch_or_buy_win_rate_pct"), 0.0)
    avg_buy_return = safe_float(row.get("avg_buy_future_20d_return_pct"), 0.0)
    avg_return = safe_float(row.get("avg_future_20d_return_pct"), 0.0)

    if status != "success" or records <= 0:
        return "NO_DATA"

    # Strongest quality: enough sample size, good win rate, good average return.
    if (
        records >= 500
        and buy_candidates >= 100
        and buy_win >= 60.0
        and avg_buy_return >= 1.5
    ):
        return "ALLOW_BUY_STRONG"

    # Normal allow: enough history and a positive edge.
    if (
        records >= 250
        and buy_candidates >= 50
        and buy_win >= 58.0
        and avg_buy_return > 0.0
    ):
        return "ALLOW_BUY"

    # Smaller sample but very interesting. Buy smaller only.
    if (
        buy_candidates >= 25
        and buy_win >= 60.0
        and avg_buy_return >= 3.0
    ):
        return "ALLOW_SMALL"

    # Watch if the broader watch/buy group is decent and returns are not ugly.
    if (
        buy_candidates >= 25
        and watch_buy_win >= 55.0
        and avg_return >= 0.0
    ):
        return "WATCH_ONLY"

    # Hard block when historical buy setups are weak or negative.
    if (
        buy_candidates >= 25
        and (buy_win < 52.0 or avg_buy_return <= 0.0)
    ):
        return "BLOCK_BUY"

    return "WATCH_ONLY"


def policy_rank(policy: str) -> int:
    ranks = {
        "NO_DATA": 0,
        "BLOCK_BUY": 1,
        "WATCH_ONLY": 2,
        "ALLOW_SMALL": 3,
        "ALLOW_BUY": 4,
        "ALLOW_BUY_STRONG": 5,
    }
    return ranks.get(policy, 0)


def read_summary_csv(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = dict(row)
            row["source_file"] = path.name
            rows.append(row)

    return rows


def choose_best(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    existing_policy = str(existing.get("master_policy", "NO_DATA"))
    new_policy = str(new.get("master_policy", "NO_DATA"))

    existing_rank = policy_rank(existing_policy)
    new_rank = policy_rank(new_policy)

    if new_rank > existing_rank:
        return new

    if new_rank < existing_rank:
        return existing

    # Tie-breaker: choose more buy candidates, then better win rate, then better return.
    existing_buy_candidates = safe_int(existing.get("buy_candidates"), 0)
    new_buy_candidates = safe_int(new.get("buy_candidates"), 0)

    if new_buy_candidates > existing_buy_candidates:
        return new

    if new_buy_candidates < existing_buy_candidates:
        return existing

    existing_win = safe_float(existing.get("buy_candidate_win_rate_pct"), 0.0)
    new_win = safe_float(new.get("buy_candidate_win_rate_pct"), 0.0)

    if new_win > existing_win:
        return new

    if new_win < existing_win:
        return existing

    existing_return = safe_float(existing.get("avg_buy_future_20d_return_pct"), 0.0)
    new_return = safe_float(new.get("avg_buy_future_20d_return_pct"), 0.0)

    if new_return > existing_return:
        return new

    return existing


def main() -> None:
    BATCH_DIR.mkdir(parents=True, exist_ok=True)

    summary_files = sorted(BATCH_DIR.glob("*summary.csv"))

    # Include the current latest summary too, in case it has not been copied yet.
    current_summary = TRAIN_DIR / "prediction_20day_daily_summary.csv"
    if current_summary.exists() and current_summary not in summary_files:
        summary_files.append(current_summary)

    if not summary_files:
        raise FileNotFoundError(f"No summary CSV files found in {BATCH_DIR}")

    print(f"Build: {BUILD}")
    print(f"Batch dir: {BATCH_DIR}")
    print(f"Summary files: {len(summary_files)}")

    by_symbol: Dict[str, Dict[str, Any]] = {}
    all_rows: List[Dict[str, Any]] = []

    for path in summary_files:
        print(f"Reading {path.name}...")
        rows = read_summary_csv(path)

        for row in rows:
            symbol = str(row.get("symbol", "")).upper().strip()
            if not symbol:
                continue

            policy = classify(row)
            row["symbol"] = symbol
            row["master_policy"] = policy

            all_rows.append(row)

            if symbol not in by_symbol:
                by_symbol[symbol] = row
            else:
                by_symbol[symbol] = choose_best(by_symbol[symbol], row)

    final_rows = list(by_symbol.values())

    final_rows.sort(
        key=lambda r: (
            policy_rank(str(r.get("master_policy", "NO_DATA"))),
            safe_float(r.get("buy_candidate_win_rate_pct"), 0.0),
            safe_float(r.get("avg_buy_future_20d_return_pct"), 0.0),
            safe_int(r.get("buy_candidates"), 0),
        ),
        reverse=True,
    )

    fieldnames = [
        "symbol",
        "master_policy",
        "status",
        "candles",
        "records",
        "buy_candidates",
        "watch",
        "avoid",
        "buy_candidate_win_rate_pct",
        "watch_or_buy_win_rate_pct",
        "avg_future_20d_return_pct",
        "avg_buy_future_20d_return_pct",
        "avg_score",
        "source_file",
    ]

    with MASTER_SUMMARY_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in final_rows:
            writer.writerow(row)

    policy = {
        str(row["symbol"]): {
            "policy": str(row.get("master_policy", "NO_DATA")),
            "records": safe_int(row.get("records"), 0),
            "buy_candidates": safe_int(row.get("buy_candidates"), 0),
            "buy_candidate_win_rate_pct": safe_float(row.get("buy_candidate_win_rate_pct"), 0.0),
            "watch_or_buy_win_rate_pct": safe_float(row.get("watch_or_buy_win_rate_pct"), 0.0),
            "avg_future_20d_return_pct": safe_float(row.get("avg_future_20d_return_pct"), 0.0),
            "avg_buy_future_20d_return_pct": safe_float(row.get("avg_buy_future_20d_return_pct"), 0.0),
            "avg_score": safe_float(row.get("avg_score"), 0.0),
            "source_file": str(row.get("source_file", "")),
        }
        for row in final_rows
    }

    counts: Dict[str, int] = {}
    for row in final_rows:
        p = str(row.get("master_policy", "NO_DATA"))
        counts[p] = counts.get(p, 0) + 1

    out = {
        "status": "complete",
        "finished_at": now_iso(),
        "build": BUILD,
        "summary_files_used": [str(p) for p in summary_files],
        "unique_symbols": len(final_rows),
        "policy_counts": counts,
        "policy": policy,
    }

    MASTER_POLICY_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")

    allow_symbols = [
        row["symbol"]
        for row in final_rows
        if str(row.get("master_policy")) in {"ALLOW_BUY_STRONG", "ALLOW_BUY", "ALLOW_SMALL"}
    ]

    strong_symbols = [
        row["symbol"]
        for row in final_rows
        if str(row.get("master_policy")) == "ALLOW_BUY_STRONG"
    ]

    small_symbols = [
        row["symbol"]
        for row in final_rows
        if str(row.get("master_policy")) == "ALLOW_SMALL"
    ]

    MASTER_ALLOW_SYMBOLS.write_text("\n".join(allow_symbols) + "\n", encoding="utf-8")
    MASTER_STRONG_ALLOW_SYMBOLS.write_text("\n".join(strong_symbols) + "\n", encoding="utf-8")
    MASTER_SMALL_ALLOW_SYMBOLS.write_text("\n".join(small_symbols) + "\n", encoding="utf-8")

    print("")
    print("DONE")
    print(json.dumps({
        "status": "complete",
        "unique_symbols": len(final_rows),
        "policy_counts": counts,
        "master_policy_path": str(MASTER_POLICY_PATH),
        "master_summary_csv": str(MASTER_SUMMARY_CSV),
        "master_allow_symbols": str(MASTER_ALLOW_SYMBOLS),
    }, indent=2))

    print("")
    print("Top master allow symbols:")
    for row in final_rows[:30]:
        if str(row.get("master_policy")) in {"ALLOW_BUY_STRONG", "ALLOW_BUY", "ALLOW_SMALL"}:
            print({
                "symbol": row.get("symbol"),
                "policy": row.get("master_policy"),
                "records": row.get("records"),
                "buy_candidates": row.get("buy_candidates"),
                "buy_win": row.get("buy_candidate_win_rate_pct"),
                "avg_buy_return": row.get("avg_buy_future_20d_return_pct"),
            })


if __name__ == "__main__":
    main()
