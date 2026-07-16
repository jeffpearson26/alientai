import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BUILD = "ALIENTAI_V2_SIMILARITY_PERCENTILE_CALIBRATOR_V1"


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


def iter_jsonl(path):
    with Path(path).open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                pass


def zscore(values, scaler):
    means = scaler["mean"]
    stds = scaler["std"]
    return [(values[i] - means[i]) / stds[i] for i in range(len(values))]


def distance(a, b):
    total = 0.0
    for x, y in zip(a, b):
        d = x - y
        total += d * d
    return math.sqrt(total / max(len(a), 1))


def blend(a, b, weight_a):
    weight_b = 1.0 - weight_a
    return [(a[i] * weight_a) + (b[i] * weight_b) for i in range(len(a))]


def score_row(row, model):
    features = model["features"]
    scaler = model["scaler"]
    prototypes = model["prototypes"]
    symbol = str(row.get("symbol") or "").upper()

    values = [safe_float(row.get(k), 0.0) for k in features]
    z = zscore(values, scaler)

    global_win = prototypes["global"]["win_centroid"]
    global_loss = prototypes["global"]["loss_centroid"]

    win_centroid = global_win
    loss_centroid = global_loss
    source = "global"

    min_symbol_proto_rows = int(model.get("settings", {}).get("min_symbol_proto_rows", 30))
    sp = prototypes["symbols"].get(symbol)

    if sp and sp.get("win_count", 0) >= min_symbol_proto_rows and sp.get("loss_count", 0) >= min_symbol_proto_rows:
        win_centroid = blend(sp["win_centroid"], global_win, 0.70)
        loss_centroid = blend(sp["loss_centroid"], global_loss, 0.70)
        source = "symbol_blended"

    d_win = distance(z, win_centroid)
    d_loss = distance(z, loss_centroid)
    edge = d_loss - d_win
    score = clamp(50.0 + edge * 18.0, 0.0, 100.0)

    return score, edge, source


def percentile_threshold(scores, top_pct):
    if not scores:
        return None

    sorted_scores = sorted(scores, reverse=True)
    n = max(1, int(math.ceil(len(sorted_scores) * (top_pct / 100.0))))
    return sorted_scores[n - 1]


def evaluate_bucket(rows, threshold):
    selected = [r for r in rows if r["score"] >= threshold]

    if not selected:
        return {
            "count": 0,
            "win_rate_pct": "",
            "avg_return_pct": "",
            "threshold": threshold,
        }

    wins = sum(1 for r in selected if r["future_return"] > 0)
    avg_return = sum(r["future_return"] for r in selected) / len(selected)

    return {
        "count": len(selected),
        "win_rate_pct": round((wins / len(selected)) * 100.0, 4),
        "avg_return_pct": round(avg_return, 6),
        "threshold": round(threshold, 6),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--feature-rows", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--split-date", default="2024-01-01")
    parser.add_argument("--min-records", type=int, default=60)
    parser.add_argument("--min-top-count", type=int, default=5)
    parser.add_argument("--min-top10-win-rate", type=float, default=55.0)
    parser.add_argument("--min-edge-over-normal", type=float, default=1.5)
    args = parser.parse_args()

    model_path = Path(args.model)
    rows_path = Path(args.feature_rows)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model = json.loads(model_path.read_text(encoding="utf-8"))

    by_symbol = defaultdict(list)

    total_rows = 0

    print("Build:", BUILD)
    print("Model:", model_path)
    print("Feature rows:", rows_path)
    print("Split date:", args.split_date)
    print("Output dir:", output_dir)
    print("This does NOT touch paper accounts or V2 trading.")
    print("")

    for row in iter_jsonl(rows_path):
        date = str(row.get("date") or "")
        if not date or date < args.split_date:
            continue

        symbol = str(row.get("symbol") or "").upper()
        if not symbol:
            continue

        score, edge, source = score_row(row, model)
        future_return = safe_float(row.get("target_return_20d_pct"), 0.0)

        by_symbol[symbol].append({
            "date": date,
            "symbol": symbol,
            "score": score,
            "edge": edge,
            "future_return": future_return,
            "source": source,
        })

        total_rows += 1

    summaries = []

    for symbol, rows in by_symbol.items():
        if len(rows) < args.min_records:
            continue

        scores = [r["score"] for r in rows]
        normal_avg_return = sum(r["future_return"] for r in rows) / len(rows)
        normal_win_rate = (sum(1 for r in rows if r["future_return"] > 0) / len(rows)) * 100.0

        top5_threshold = percentile_threshold(scores, 5.0)
        top10_threshold = percentile_threshold(scores, 10.0)
        top20_threshold = percentile_threshold(scores, 20.0)

        top5 = evaluate_bucket(rows, top5_threshold)
        top10 = evaluate_bucket(rows, top10_threshold)
        top20 = evaluate_bucket(rows, top20_threshold)

        top10_count = int(top10["count"] or 0)
        top10_win = safe_float(top10["win_rate_pct"], 0.0)
        top10_avg = safe_float(top10["avg_return_pct"], 0.0)
        edge_over_normal = top10_avg - normal_avg_return

        if (
            top10_count >= args.min_top_count
            and top10_win >= args.min_top10_win_rate
            and edge_over_normal >= args.min_edge_over_normal
        ):
            policy = "ALLOW_BUY"
        elif top10_count >= args.min_top_count and top10_avg > normal_avg_return:
            policy = "WATCH_ONLY"
        else:
            policy = "BLOCK_BUY"

        summaries.append({
            "symbol": symbol,
            "records": len(rows),
            "normal_win_rate_pct": round(normal_win_rate, 4),
            "normal_avg_20d_return_pct": round(normal_avg_return, 6),
            "top5_count": top5["count"],
            "top5_score_threshold": top5["threshold"],
            "top5_win_rate_pct": top5["win_rate_pct"],
            "top5_avg_20d_return_pct": top5["avg_return_pct"],
            "top10_count": top10["count"],
            "top10_score_threshold": top10["threshold"],
            "top10_win_rate_pct": top10["win_rate_pct"],
            "top10_avg_20d_return_pct": top10["avg_return_pct"],
            "top10_edge_over_normal_pct": round(edge_over_normal, 6),
            "top20_count": top20["count"],
            "top20_score_threshold": top20["threshold"],
            "top20_win_rate_pct": top20["win_rate_pct"],
            "top20_avg_20d_return_pct": top20["avg_return_pct"],
            "max_score": round(max(scores), 6),
            "avg_score": round(sum(scores) / len(scores), 6),
            "policy": policy,
        })

    summaries.sort(
        key=lambda r: (
            0 if r["policy"] == "ALLOW_BUY" else 1 if r["policy"] == "WATCH_ONLY" else 2,
            -safe_float(r["top10_win_rate_pct"], 0.0),
            -safe_float(r["top10_avg_20d_return_pct"], 0.0),
            -safe_float(r["top10_edge_over_normal_pct"], 0.0),
        )
    )

    summary_csv = output_dir / "similarity_percentile_symbol_summary.csv"
    summary_json = output_dir / "similarity_percentile_training_summary.json"
    allowed_path = output_dir / "similarity_percentile_allowed_symbols.txt"
    watch_path = output_dir / "similarity_percentile_watch_symbols.txt"
    block_path = output_dir / "similarity_percentile_block_symbols.txt"

    fields = [
        "symbol",
        "records",
        "normal_win_rate_pct",
        "normal_avg_20d_return_pct",
        "top5_count",
        "top5_score_threshold",
        "top5_win_rate_pct",
        "top5_avg_20d_return_pct",
        "top10_count",
        "top10_score_threshold",
        "top10_win_rate_pct",
        "top10_avg_20d_return_pct",
        "top10_edge_over_normal_pct",
        "top20_count",
        "top20_score_threshold",
        "top20_win_rate_pct",
        "top20_avg_20d_return_pct",
        "max_score",
        "avg_score",
        "policy",
    ]

    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summaries)

    allowed = [r["symbol"] for r in summaries if r["policy"] == "ALLOW_BUY"]
    watch = [r["symbol"] for r in summaries if r["policy"] == "WATCH_ONLY"]
    block = [r["symbol"] for r in summaries if r["policy"] == "BLOCK_BUY"]

    allowed_path.write_text("\n".join(allowed) + ("\n" if allowed else ""), encoding="utf-8")
    watch_path.write_text("\n".join(watch) + ("\n" if watch else ""), encoding="utf-8")
    block_path.write_text("\n".join(block) + ("\n" if block else ""), encoding="utf-8")

    report = {
        "status": "complete",
        "finished_at": now_iso(),
        "build": BUILD,
        "model": str(model_path),
        "feature_rows": str(rows_path),
        "split_date": args.split_date,
        "total_eval_rows": total_rows,
        "symbols_evaluated": len(summaries),
        "policy_counts": {
            "allow_buy": len(allowed),
            "watch_only": len(watch),
            "block_buy": len(block),
        },
        "summary_csv": str(summary_csv),
        "allowed_symbols_path": str(allowed_path),
        "watch_symbols_path": str(watch_path),
        "block_symbols_path": str(block_path),
        "settings": vars(args),
    }

    summary_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("")
    print("DONE")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
