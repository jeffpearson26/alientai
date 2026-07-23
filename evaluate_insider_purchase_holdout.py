from __future__ import annotations

"""Read-only holdout evaluation of precomputed SEC Form 4 purchase features."""

import argparse
import json
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping, Sequence


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def metrics(rows: Sequence[Mapping[str, Any]], cost_pct: float) -> dict[str, Any]:
    values = [float(row["label_forward_return_5d_pct"]) - cost_pct for row in rows]
    return {
        "signals": len(values),
        "mean_net_return_pct": round(mean(values), 6) if values else None,
        "median_net_return_pct": round(median(values), 6) if values else None,
        "win_rate_after_cost": round(sum(value > 0 for value in values) / len(values), 6) if values else None,
        "exceptional_winner_rate": round(sum(float(row["label_forward_return_5d_pct"]) >= 10.0 for row in rows) / len(rows), 6) if rows else None,
    }


def evaluate(rows: Sequence[Mapping[str, Any]], holdout_year: str, cost_pct: float) -> dict[str, Any]:
    holdout = [row for row in rows if str(row.get("market_date") or "").startswith(holdout_year)]
    available = [row for row in holdout if row.get("insider_purchase_available")]
    large = [row for row in available if row.get("insider_large_purchase_30d")]
    cluster = [row for row in available if row.get("insider_cluster_buy_30d")]
    return {
        "status": "complete", "research_only": True, "execution_enabled": False,
        "warning": "Holdout association study only; SEC Form 4 features cannot independently enable selection.",
        "holdout_year": holdout_year, "round_trip_cost_pct": cost_pct,
        "full_universe": metrics(holdout, cost_pct), "availability_matched_universe": metrics(available, cost_pct),
        "large_purchase_30d": metrics(large, cost_pct), "cluster_buy_30d": metrics(cluster, cost_pct),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Form 4 purchase features on a later calendar-year holdout.")
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--holdout-year", required=True)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(read_jsonl(args.rows), args.holdout_year, args.round_trip_cost_pct)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
