from __future__ import annotations

"""Evaluate executable per-day rank policies for the 20-minute models."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from evaluate_ai_semiconductor_ablations import select_partition
from train_natural_technical_context import matrix, read_jsonl


FRACTIONS = (0.10, 0.20, 0.30, 0.50)


def max_drawdown(returns_pct: Sequence[float]) -> float:
    equity = peak = 1.0
    worst = 0.0
    for value in returns_pct:
        equity *= 1.0 + value / 100.0
        peak = max(peak, equity)
        worst = min(worst, (equity / peak - 1.0) * 100.0)
    return worst


def daily_policy_metrics(
    rows: Sequence[Mapping[str, Any]],
    scores: np.ndarray,
    target: str,
    fraction: float,
) -> dict[str, Any]:
    by_date: dict[str, list[tuple[Mapping[str, Any], float]]] = defaultdict(list)
    for row, score in zip(rows, scores):
        by_date[str(row["market_date"])].append((row, float(score)))
    selected_returns, daily_returns, selected_counts = [], [], []
    for day in sorted(by_date):
        ranked = sorted(by_date[day], key=lambda item: (-item[1], str(item[0]["symbol"])))
        count = max(1, int(np.ceil(len(ranked) * fraction)))
        values = [float(row[target]) for row, _ in ranked[:count]]
        selected_returns.extend(values)
        daily_returns.append(float(np.mean(values)))
        selected_counts.append(count)
    return {
        "dates": len(daily_returns),
        "trades": len(selected_returns),
        "mean_trades_per_day": round(float(np.mean(selected_counts)), 6),
        "positive_trade_rate": round(sum(value > 0 for value in selected_returns) / len(selected_returns), 6),
        "mean_trade_net_return_pct": round(float(np.mean(selected_returns)), 6),
        "median_trade_net_return_pct": round(float(np.median(selected_returns)), 6),
        "positive_day_rate": round(sum(value > 0 for value in daily_returns) / len(daily_returns), 6),
        "mean_daily_net_return_pct": round(float(np.mean(daily_returns)), 6),
        "cumulative_compounded_return_pct": round(
            (float(np.prod([1.0 + value / 100.0 for value in daily_returns])) - 1.0) * 100.0, 6
        ),
        "max_drawdown_pct": round(max_drawdown(daily_returns), 6),
    }


def evaluate(panel: Path, model_dirs: Sequence[Path], target: str) -> dict[str, Any]:
    rows = [row for row in read_jsonl(panel) if row.get(target) is not None]
    output: dict[str, Any] = {}
    for directory in model_dirs:
        report = json.loads((directory / "natural_technical_context_report.json").read_text(encoding="utf-8"))
        model = lgb.Booster(model_file=str(directory / "natural_technical_context_classifier.txt"))
        partitions = {
            name: select_partition(rows, report["split"], name)
            for name in ("validation", "test")
        }
        metrics = {}
        for name, selected in partitions.items():
            scores = model.predict(matrix(selected, report["feature_names"]), num_iteration=model.best_iteration)
            metrics[name] = {
                str(fraction): daily_policy_metrics(selected, scores, target, fraction)
                for fraction in FRACTIONS
            }
        selected_fraction = max(
            (str(fraction) for fraction in FRACTIONS),
            key=lambda fraction: metrics["validation"][fraction]["mean_daily_net_return_pct"],
        )
        output[directory.name] = {
            "selected_fraction_from_validation": selected_fraction,
            "validation": metrics["validation"][selected_fraction],
            "test": metrics["test"][selected_fraction],
            "all_fractions": metrics,
        }
    return {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "policy": "rank each date independently; fraction selected on validation only",
        "target": target,
        "models": output,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, action="append", required=True)
    parser.add_argument("--target", default="label_forward_return_20m_net_pct")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.panel, args.model_dir, args.target)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
