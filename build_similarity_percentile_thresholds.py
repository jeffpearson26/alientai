import csv
import json
from pathlib import Path
from datetime import datetime

csv_path = Path("data_v2/similarity_engine_training/sp500_percentile_v1/similarity_percentile_sandbox_strict_candidates.csv")
out_path = Path("data_v2/similarity_engine_training/sp500_percentile_v1/similarity_percentile_sandbox_thresholds.json")

if not csv_path.exists():
    raise SystemExit(f"Missing strict candidates CSV: {csv_path}")

thresholds = {}

with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        symbol = row["symbol"].strip().upper()
        thresholds[symbol] = {
            "symbol": symbol,
            "top10_score_threshold": float(row["top10_score_threshold"]),
            "top10_win_rate_pct": float(row["top10_win_rate_pct"]),
            "top10_avg_20d_return_pct": float(row["top10_avg_20d_return_pct"]),
            "top10_edge_over_normal_pct": float(row["top10_edge_over_normal_pct"]),
            "top5_win_rate_pct": float(row["top5_win_rate_pct"]),
            "top5_avg_20d_return_pct": float(row["top5_avg_20d_return_pct"]),
            "normal_avg_20d_return_pct": float(row["normal_avg_20d_return_pct"]),
            "records": int(float(row["records"])),
            "top10_count": int(float(row["top10_count"])),
        }

payload = {
    "build": "ALIENTAI_V2_SIMILARITY_PERCENTILE_SANDBOX_THRESHOLDS_V1",
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "source_csv": str(csv_path),
    "symbol_count": len(thresholds),
    "threshold_mode": "symbol_specific_top10_score_threshold",
    "symbols": thresholds,
    "note": "Use each symbol's own top10_score_threshold instead of a universal similarity score threshold."
}

out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

print("Wrote percentile sandbox thresholds.")
print("Output:", out_path)
print("Symbols:", len(thresholds))
print("")
for sym, data in thresholds.items():
    print(
        sym,
        "threshold=", data["top10_score_threshold"],
        "win%=", data["top10_win_rate_pct"],
        "avg20d=", data["top10_avg_20d_return_pct"],
        "edge=", data["top10_edge_over_normal_pct"],
    )
