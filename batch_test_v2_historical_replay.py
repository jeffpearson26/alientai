from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


FOLDER = Path(r"C:\Users\jeffp\AlientAI_Start_Over_8010\archive_more_old_outputs_20260706_211532\intraday_test_data_5m")
OUT_CSV = Path(r"data_v2\v2_batch_replay_summary.csv")
OUT_JSON = Path(r"data_v2\v2_batch_replay_summary.json")


def symbol_from_file(path: Path) -> str:
    name = path.name
    return name.replace("_schwab_5m_10d.csv", "").upper()


def main() -> None:
    rows = []
    files = sorted(FOLDER.glob("*_schwab_5m_10d.csv"))

    for file_path in files:
        symbol = symbol_from_file(file_path)

        cmd = [
            sys.executable,
            "test_v2_historical_replay.py",
            "--csv",
            str(file_path),
            "--max-rows",
            "5000",
            "--out",
            "data_v2/v2_historical_replay_report_tmp.json",
        ]

        print(f"Testing {symbol}...")
        completed = subprocess.run(cmd, capture_output=True, text=True)

        if completed.returncode != 0:
            rows.append({
                "symbol": symbol,
                "engine_id": "ERROR",
                "trades": 0,
                "outcomes_available": 0,
                "wins": 0,
                "losses": 0,
                "win_rate_pct": "",
                "avg_pnl_pct": "",
                "error": completed.stderr[-500:],
            })
            continue

        report_path = Path("data_v2/v2_historical_replay_report_tmp.json")
        report = json.loads(report_path.read_text(encoding="utf-8"))

        summaries = report.get("summary_by_engine", [])

        if not summaries:
            rows.append({
                "symbol": symbol,
                "engine_id": "NO_TRADES",
                "trades": 0,
                "outcomes_available": 0,
                "wins": 0,
                "losses": 0,
                "win_rate_pct": "",
                "avg_pnl_pct": "",
                "error": "",
            })
            continue

        for s in summaries:
            rows.append({
                "symbol": symbol,
                "engine_id": s.get("engine_id"),
                "trades": s.get("trades"),
                "outcomes_available": s.get("outcomes_available"),
                "wins": s.get("wins"),
                "losses": s.get("losses"),
                "win_rate_pct": s.get("win_rate_pct"),
                "avg_pnl_pct": s.get("avg_pnl_pct"),
                "error": "",
            })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "symbol",
            "engine_id",
            "trades",
            "outcomes_available",
            "wins",
            "losses",
            "win_rate_pct",
            "avg_pnl_pct",
            "error",
        ])
        writer.writeheader()
        writer.writerows(rows)

    OUT_JSON.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    print(f"\nDone.")
    print(f"CSV:  {OUT_CSV}")
    print(f"JSON: {OUT_JSON}")

    print("\nTop positive momentum_5min rows:")
    positive = [
        r for r in rows
        if r.get("engine_id") == "momentum_5min"
        and isinstance(r.get("avg_pnl_pct"), (int, float))
        and r.get("outcomes_available", 0)
    ]
    positive.sort(key=lambda r: float(r["avg_pnl_pct"]), reverse=True)

    for r in positive[:20]:
        print(r)


if __name__ == "__main__":
    main()
