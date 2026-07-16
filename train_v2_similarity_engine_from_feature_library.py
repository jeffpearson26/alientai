import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BUILD = "ALIENTAI_V2_SIMILARITY_ENGINE_FEATURE_LIBRARY_TRAINER_V1"

FEATURES = [
    "return_1d_pct",
    "return_5d_pct",
    "return_20d_pct",
    "return_60d_pct",
    "range_pct",
    "body_pct",
    "gap_pct",
    "volume_ratio_20d",
    "close_vs_sma20_pct",
    "close_vs_sma50_pct",
    "close_vs_sma200_pct",
    "rsi14",
    "macd_hist",
    "atr14_pct",
    "distance_from_20d_high_pct",
    "distance_from_20d_low_pct",
    "distance_from_60d_high_pct",
    "distance_from_60d_low_pct",
]


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default


def clamp(value, low, high):
    return max(low, min(high, value))


def find_feature_files(feature_dirs):
    paths = []
    for item in feature_dirs:
        p = Path(item)
        if p.is_file() and p.name.endswith(".jsonl"):
            paths.append(p)
        elif p.is_dir():
            direct = p / "daily_feature_rows.jsonl"
            if direct.exists():
                paths.append(direct)
            else:
                paths.extend(list(p.rglob("daily_feature_rows.jsonl")))

    unique = []
    seen = set()
    for p in paths:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def iter_rows(paths):
    for path in paths:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    pass


def get_values(row):
    return [safe_float(row.get(k), 0.0) for k in FEATURES]


def vector_add(a, b):
    for i, value in enumerate(b):
        a[i] += value


def vector_div(a, n):
    if n <= 0:
        return [0.0 for _ in a]
    return [x / n for x in a]


def distance(a, b):
    total = 0.0
    for x, y in zip(a, b):
        d = x - y
        total += d * d
    return math.sqrt(total / max(len(a), 1))


def compute_scaler(paths, split_date, train_step):
    count = 0
    sums = [0.0] * len(FEATURES)
    sums_sq = [0.0] * len(FEATURES)
    per_symbol_count = defaultdict(int)

    for row in iter_rows(paths):
        date = str(row.get("date") or "")
        if not date or date >= split_date:
            continue

        sym = str(row.get("symbol") or "").upper()
        per_symbol_count[sym] += 1
        if train_step > 1 and per_symbol_count[sym] % train_step != 0:
            continue

        values = get_values(row)
        count += 1

        for i, value in enumerate(values):
            sums[i] += value
            sums_sq[i] += value * value

    if count < 100:
        raise SystemExit("Not enough training rows before split date.")

    means = []
    stds = []

    for i in range(len(FEATURES)):
        mean = sums[i] / count
        variance = (sums_sq[i] / count) - (mean * mean)
        std = math.sqrt(max(variance, 1e-9))
        if std < 1e-9:
            std = 1.0
        means.append(mean)
        stds.append(std)

    return {
        "features": FEATURES,
        "row_count": count,
        "mean": means,
        "std": stds,
    }


def zscore(values, scaler):
    return [
        (values[i] - scaler["mean"][i]) / scaler["std"][i]
        for i in range(len(values))
    ]


def build_prototypes(paths, scaler, split_date, train_step, strong_up_pct, strong_down_pct):
    dim = len(FEATURES)

    global_win_sum = [0.0] * dim
    global_loss_sum = [0.0] * dim
    global_win_count = 0
    global_loss_count = 0

    symbol_data = defaultdict(lambda: {
        "win_sum": [0.0] * dim,
        "loss_sum": [0.0] * dim,
        "win_count": 0,
        "loss_count": 0,
    })

    per_symbol_count = defaultdict(int)

    for row in iter_rows(paths):
        date = str(row.get("date") or "")
        if not date or date >= split_date:
            continue

        sym = str(row.get("symbol") or "").upper()
        if not sym:
            continue

        per_symbol_count[sym] += 1
        if train_step > 1 and per_symbol_count[sym] % train_step != 0:
            continue

        future_return = safe_float(row.get("target_return_20d_pct"), 0.0)
        z = zscore(get_values(row), scaler)

        if future_return >= strong_up_pct:
            vector_add(global_win_sum, z)
            global_win_count += 1
            vector_add(symbol_data[sym]["win_sum"], z)
            symbol_data[sym]["win_count"] += 1

        elif future_return <= strong_down_pct:
            vector_add(global_loss_sum, z)
            global_loss_count += 1
            vector_add(symbol_data[sym]["loss_sum"], z)
            symbol_data[sym]["loss_count"] += 1

    if global_win_count == 0 or global_loss_count == 0:
        raise SystemExit("Could not build winner/loser prototypes.")

    symbols = {}
    for sym, data in symbol_data.items():
        symbols[sym] = {
            "win_count": data["win_count"],
            "loss_count": data["loss_count"],
            "win_centroid": vector_div(data["win_sum"], data["win_count"]),
            "loss_centroid": vector_div(data["loss_sum"], data["loss_count"]),
        }

    return {
        "global": {
            "win_count": global_win_count,
            "loss_count": global_loss_count,
            "win_centroid": vector_div(global_win_sum, global_win_count),
            "loss_centroid": vector_div(global_loss_sum, global_loss_count),
        },
        "symbols": symbols,
    }


def blend(a, b, weight_a):
    weight_b = 1.0 - weight_a
    return [(a[i] * weight_a) + (b[i] * weight_b) for i in range(len(a))]


def score_row(row, scaler, prototypes, min_symbol_proto_rows):
    sym = str(row.get("symbol") or "").upper()
    z = zscore(get_values(row), scaler)

    global_win = prototypes["global"]["win_centroid"]
    global_loss = prototypes["global"]["loss_centroid"]

    win_centroid = global_win
    loss_centroid = global_loss
    source = "global"

    sp = prototypes["symbols"].get(sym)
    if sp and sp["win_count"] >= min_symbol_proto_rows and sp["loss_count"] >= min_symbol_proto_rows:
        win_centroid = blend(sp["win_centroid"], global_win, 0.70)
        loss_centroid = blend(sp["loss_centroid"], global_loss, 0.70)
        source = "symbol_blended"

    d_win = distance(z, win_centroid)
    d_loss = distance(z, loss_centroid)

    edge = d_loss - d_win
    score = clamp(50.0 + edge * 18.0, 0.0, 100.0)

    return score, edge, source


def evaluate(paths, scaler, prototypes, split_date, eval_step, min_symbol_proto_rows, buy_score, watch_score):
    stats = defaultdict(lambda: {
        "records": 0,
        "wins": 0,
        "buy_candidates": 0,
        "buy_wins": 0,
        "watch": 0,
        "avoid": 0,
        "watch_or_buy": 0,
        "watch_or_buy_wins": 0,
        "future_sum": 0.0,
        "buy_future_sum": 0.0,
        "score_sum": 0.0,
        "max_score": 0.0,
        "prototype_sources": defaultdict(int),
    })

    per_symbol_count = defaultdict(int)
    total_eval_rows = 0

    for row in iter_rows(paths):
        date = str(row.get("date") or "")
        if not date or date < split_date:
            continue

        sym = str(row.get("symbol") or "").upper()
        if not sym:
            continue

        per_symbol_count[sym] += 1
        if eval_step > 1 and per_symbol_count[sym] % eval_step != 0:
            continue

        future_return = safe_float(row.get("target_return_20d_pct"), 0.0)
        win = future_return > 0

        score, edge, source = score_row(row, scaler, prototypes, min_symbol_proto_rows)

        s = stats[sym]
        s["records"] += 1
        s["future_sum"] += future_return
        s["score_sum"] += score
        s["max_score"] = max(s["max_score"], score)
        s["prototype_sources"][source] += 1

        if win:
            s["wins"] += 1

        if score >= buy_score:
            s["buy_candidates"] += 1
            s["buy_future_sum"] += future_return
            if win:
                s["buy_wins"] += 1
        elif score >= watch_score:
            s["watch"] += 1
        else:
            s["avoid"] += 1

        if score >= watch_score:
            s["watch_or_buy"] += 1
            if win:
                s["watch_or_buy_wins"] += 1

        total_eval_rows += 1

    rows = []

    for sym, s in stats.items():
        records = s["records"]
        buy_candidates = s["buy_candidates"]
        watch_or_buy = s["watch_or_buy"]

        buy_win_rate = ""
        if buy_candidates:
            buy_win_rate = round((s["buy_wins"] / buy_candidates) * 100.0, 4)

        watch_or_buy_win_rate = ""
        if watch_or_buy:
            watch_or_buy_win_rate = round((s["watch_or_buy_wins"] / watch_or_buy) * 100.0, 4)

        avg_future = round(s["future_sum"] / records, 6) if records else ""
        avg_buy_future = round(s["buy_future_sum"] / buy_candidates, 6) if buy_candidates else ""
        avg_score = round(s["score_sum"] / records, 6) if records else ""

        rows.append({
            "symbol": sym,
            "records": records,
            "buy_candidates": buy_candidates,
            "watch": s["watch"],
            "avoid": s["avoid"],
            "buy_candidate_win_rate_pct": buy_win_rate,
            "watch_or_buy_win_rate_pct": watch_or_buy_win_rate,
            "avg_future_20d_return_pct": avg_future,
            "avg_buy_future_20d_return_pct": avg_buy_future,
            "avg_score": avg_score,
            "max_score": round(s["max_score"], 6),
            "prototype_sources": dict(s["prototype_sources"]),
        })

    return rows, total_eval_rows


def policy_for(row, min_records, min_buy_candidates, allow_win_rate, watch_win_rate):
    records = int(row.get("records") or 0)
    buy_candidates = int(row.get("buy_candidates") or 0)
    buy_win = safe_float(row.get("buy_candidate_win_rate_pct"), 0.0)
    watch_win = safe_float(row.get("watch_or_buy_win_rate_pct"), 0.0)
    avg_buy_return = safe_float(row.get("avg_buy_future_20d_return_pct"), 0.0)
    avg_return = safe_float(row.get("avg_future_20d_return_pct"), 0.0)

    if records >= min_records and buy_candidates >= min_buy_candidates and buy_win >= allow_win_rate and avg_buy_return > 0:
        return "ALLOW_BUY"

    if records >= min_records and watch_win >= watch_win_rate and avg_return > 0:
        return "WATCH_ONLY"

    return "BLOCK_BUY"


def write_csv(path, rows):
    fields = [
        "symbol",
        "records",
        "buy_candidates",
        "watch",
        "avoid",
        "buy_candidate_win_rate_pct",
        "watch_or_buy_win_rate_pct",
        "avg_future_20d_return_pct",
        "avg_buy_future_20d_return_pct",
        "avg_score",
        "max_score",
        "policy",
        "prototype_sources",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["prototype_sources"] = json.dumps(out.get("prototype_sources", {}), separators=(",", ":"))
            writer.writerow({k: out.get(k, "") for k in fields})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature-dir", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--split-date", default="2024-01-01")
    parser.add_argument("--train-step", type=int, default=5)
    parser.add_argument("--eval-step", type=int, default=5)
    parser.add_argument("--strong-up-pct", type=float, default=3.0)
    parser.add_argument("--strong-down-pct", type=float, default=-3.0)
    parser.add_argument("--buy-score", type=float, default=60.0)
    parser.add_argument("--watch-score", type=float, default=55.0)
    parser.add_argument("--min-symbol-proto-rows", type=int, default=30)
    parser.add_argument("--min-records", type=int, default=60)
    parser.add_argument("--min-buy-candidates", type=int, default=10)
    parser.add_argument("--allow-win-rate", type=float, default=58.0)
    parser.add_argument("--watch-win-rate", type=float, default=55.0)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    feature_paths = find_feature_files(args.feature_dir)
    if not feature_paths:
        raise SystemExit("No daily_feature_rows.jsonl files found.")

    print("Build:", BUILD)
    print("Feature files:")
    for p in feature_paths:
        print(" ", p)
    print("Output dir:", output_dir)
    print("Split date:", args.split_date)
    print("This does NOT touch V2 paper trading.")
    print("")

    print("Pass 1/3: computing scaler...")
    scaler = compute_scaler(feature_paths, args.split_date, args.train_step)
    print("  scaler rows:", scaler["row_count"])

    print("Pass 2/3: building similarity prototypes...")
    prototypes = build_prototypes(
        feature_paths,
        scaler,
        args.split_date,
        args.train_step,
        args.strong_up_pct,
        args.strong_down_pct,
    )
    print("  global winners:", prototypes["global"]["win_count"])
    print("  global losers:", prototypes["global"]["loss_count"])
    print("  symbol prototypes:", len(prototypes["symbols"]))

    print("Pass 3/3: evaluating out-of-sample rows...")
    summaries, total_eval_rows = evaluate(
        feature_paths,
        scaler,
        prototypes,
        args.split_date,
        args.eval_step,
        args.min_symbol_proto_rows,
        args.buy_score,
        args.watch_score,
    )

    for row in summaries:
        row["policy"] = policy_for(
            row,
            args.min_records,
            args.min_buy_candidates,
            args.allow_win_rate,
            args.watch_win_rate,
        )

    summaries.sort(
        key=lambda r: (
            0 if r["policy"] == "ALLOW_BUY" else 1 if r["policy"] == "WATCH_ONLY" else 2,
            -safe_float(r.get("buy_candidate_win_rate_pct"), 0.0),
            -safe_float(r.get("avg_buy_future_20d_return_pct"), 0.0),
        )
    )

    allow_symbols = [r["symbol"] for r in summaries if r["policy"] == "ALLOW_BUY"]
    watch_symbols = [r["symbol"] for r in summaries if r["policy"] == "WATCH_ONLY"]
    block_symbols = [r["symbol"] for r in summaries if r["policy"] == "BLOCK_BUY"]

    model = {
        "build": BUILD,
        "created_at": now_iso(),
        "features": FEATURES,
        "split_date": args.split_date,
        "settings": vars(args),
        "scaler": scaler,
        "prototypes": prototypes,
        "policy_counts": {
            "allow_buy": len(allow_symbols),
            "watch_only": len(watch_symbols),
            "block_buy": len(block_symbols),
        },
    }

    model_path = output_dir / "similarity_engine_model.json"
    summary_csv_path = output_dir / "similarity_engine_symbol_summary.csv"
    summary_json_path = output_dir / "similarity_engine_training_summary.json"
    allow_path = output_dir / "similarity_engine_allowed_symbols.txt"
    watch_path = output_dir / "similarity_engine_watch_only_symbols.txt"
    block_path = output_dir / "similarity_engine_block_symbols.txt"

    model_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
    write_csv(summary_csv_path, summaries)
    allow_path.write_text("\n".join(allow_symbols) + ("\n" if allow_symbols else ""), encoding="utf-8")
    watch_path.write_text("\n".join(watch_symbols) + ("\n" if watch_symbols else ""), encoding="utf-8")
    block_path.write_text("\n".join(block_symbols) + ("\n" if block_symbols else ""), encoding="utf-8")

    report = {
        "status": "complete",
        "finished_at": now_iso(),
        "build": BUILD,
        "feature_files": [str(p) for p in feature_paths],
        "output_dir": str(output_dir),
        "split_date": args.split_date,
        "total_eval_rows": total_eval_rows,
        "symbols_evaluated": len(summaries),
        "policy_counts": {
            "allow_buy": len(allow_symbols),
            "watch_only": len(watch_symbols),
            "block_buy": len(block_symbols),
        },
        "model_path": str(model_path),
        "summary_csv": str(summary_csv_path),
        "allowed_symbols_path": str(allow_path),
        "watch_only_symbols_path": str(watch_path),
        "block_symbols_path": str(block_path),
        "settings": vars(args),
    }

    summary_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("")
    print("DONE")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
