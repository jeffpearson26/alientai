from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parent
SUMMARY_CSV = PROJECT_ROOT / "data_v2" / "similarity_replay_training" / "similarity_walk_forward_summary.csv"
OUT_JSON = PROJECT_ROOT / "data_v2" / "similarity_replay_training" / "similarity_symbol_policy.json"
OUT_TXT = PROJECT_ROOT / "data_v2" / "similarity_replay_training" / "similarity_allow_symbols.txt"


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


def main() -> None:
    rows: List[Dict[str, Any]] = []

    with SUMMARY_CSV.open("r", encoding="utf-8-sig", newline="") as f:
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
        prediction_win_rate = safe_float(row.get("prediction_win_rate_pct"))
        buy_win_rate = safe_float(row.get("buy_candidate_win_rate_pct"))
        avg_forward = safe_float(row.get("avg_forward_return_pct"))
        avg_score = safe_float(row.get("avg_score"))

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
        "build": "ALIENTAI_V2_SIMILARITY_SYMBOL_POLICY_V1",
        "source": str(SUMMARY_CSV),
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

    OUT_JSON.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    OUT_TXT.write_text("\n".join(policy["allow_symbols"]) + "\n", encoding="utf-8")

    print(json.dumps(policy["counts"], indent=2))
    print("")
    print("Top allow symbols:")
    for item in allow[:40]:
        print(item)
    print("")
    print(f"Wrote: {OUT_JSON}")
    print(f"Wrote: {OUT_TXT}")


if __name__ == "__main__":
    main()
