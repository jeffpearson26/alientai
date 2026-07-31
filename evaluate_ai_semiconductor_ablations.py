from __future__ import annotations

"""Evaluate catalyst ablations with useful basket sizes and net returns."""

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from train_natural_technical_context import matrix, read_jsonl


def basket_metrics(rows: Sequence[Mapping[str, Any]], scores: np.ndarray, target: str) -> dict[str, Any]:
    order = np.argsort(-scores)
    result: dict[str, Any] = {}
    for fraction in (0.10, 0.20, 0.30, 0.50, 1.0):
        count = max(1, int(np.ceil(len(rows) * fraction)))
        selected = [float(rows[index][target]) for index in order[:count]]
        result[str(fraction)] = {
            "count": count,
            "winner_rate_5pct": round(sum(value >= 5.0 for value in selected) / count, 6),
            "positive_rate": round(sum(value > 0 for value in selected) / count, 6),
            "mean_net_return_pct": round(float(np.mean(selected)), 6),
            "median_net_return_pct": round(float(np.median(selected)), 6),
        }
    return result


def select_partition(rows: Sequence[Mapping[str, Any]], split: Mapping[str, str], name: str) -> list[Mapping[str, Any]]:
    if name == "validation":
        start, end = date.fromisoformat(split["validation_start"]), date.fromisoformat(split["validation_end"])
        return [row for row in rows if start <= date.fromisoformat(row["market_date"]) <= end]
    start = date.fromisoformat(split["test_start"])
    return [row for row in rows if date.fromisoformat(row["market_date"]) >= start]


def evaluate(panel: Path, model_dirs: Sequence[Path], target: str) -> dict[str, Any]:
    rows = [row for row in read_jsonl(panel) if row.get(target) is not None]
    models: dict[str, Any] = {}
    for directory in model_dirs:
        report = json.loads((directory / "natural_technical_context_report.json").read_text(encoding="utf-8"))
        model = lgb.Booster(model_file=str(directory / "natural_technical_context_classifier.txt"))
        partitions = {}
        for name in ("validation", "test"):
            selected = select_partition(rows, report["split"], name)
            scores = model.predict(matrix(selected, report["feature_names"]), num_iteration=model.best_iteration)
            partitions[name] = basket_metrics(selected, scores, target)
        models[directory.name] = {
            "best_iteration": model.best_iteration,
            "feature_count": len(report["feature_names"]),
            **partitions,
        }
    return {
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "warning": "Small prototype panel; test results are insufficient for paper-trading authorization.",
        "panel": str(panel),
        "target": target,
        "models": models,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, action="append", required=True)
    parser.add_argument("--target", default="label_forward_return_5d_av_net_pct")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.panel, args.model_dir, args.target)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
