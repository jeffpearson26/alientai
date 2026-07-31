from __future__ import annotations

"""Summarize frozen intraday prospective outcomes without tuning the models."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from evaluate_ai_semiconductor_intraday_daily_policy import max_drawdown


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def summarize(rows: Sequence[Mapping[str, Any]], minimum_days: int = 20) -> dict[str, Any]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["model_id"])].append(row)
    models = {}
    for model_id, model_rows in sorted(grouped.items()):
        by_date: dict[str, list[float]] = defaultdict(list)
        trade_returns = []
        for row in model_rows:
            target = f"label_forward_return_{int(row['horizon_minutes'])}m_net_pct"
            value = float(row[target])
            trade_returns.append(value)
            by_date[str(row["market_date"])].append(value)
        daily_returns = [float(np.mean(by_date[day])) for day in sorted(by_date)]
        models[model_id] = {
            "horizon_minutes": int(model_rows[0]["horizon_minutes"]),
            "days": len(daily_returns),
            "trades": len(trade_returns),
            "minimum_days_required": minimum_days,
            "evidence_gate_met": len(daily_returns) >= minimum_days,
            "positive_trade_rate": round(sum(value > 0 for value in trade_returns) / len(trade_returns), 6),
            "mean_trade_net_return_pct": round(float(np.mean(trade_returns)), 6),
            "positive_day_rate": round(sum(value > 0 for value in daily_returns) / len(daily_returns), 6),
            "mean_daily_net_return_pct": round(float(np.mean(daily_returns)), 6),
            "compounded_return_pct": round(
                (float(np.prod([1.0 + value / 100.0 for value in daily_returns])) - 1.0) * 100.0,
                6,
            ),
            "max_drawdown_pct": round(max_drawdown(daily_returns), 6),
        }
    return {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "models": models,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--minimum-days", type=int, default=20)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(read_jsonl(args.outcomes), args.minimum_days)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
