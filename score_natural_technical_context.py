from __future__ import annotations

"""Score a point-in-time technical panel with the research-only context model."""

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import lightgbm as lgb
import numpy as np

from alientai_v2.features.insider_purchase_features import safe_float


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def score_rows(rows: Sequence[Mapping[str, Any]], feature_names: Sequence[str], model: Any) -> list[dict[str, Any]]:
    missing = sorted({name for name in feature_names if any(name not in row for row in rows)})
    if missing:
        raise ValueError(f"panel is missing required model features: {', '.join(missing)}")
    values = np.column_stack([
        np.asarray([safe_float(row.get(name)) for row in rows], dtype=np.float32)
        for name in feature_names
    ])
    scores = model.predict(values)
    return [{**row, "technical_context_score": float(score), "research_only": True} for row, score in zip(rows, scores)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a technical panel for research only.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = read_jsonl(args.input)
    if not rows:
        raise ValueError("input panel must contain at least one row")
    model = lgb.Booster(model_file=str(args.model))
    scored = score_rows(rows, model.feature_name(), model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in scored), encoding="utf-8")
    print(json.dumps({"status": "complete", "research_only": True, "rows": len(scored),
                      "minimum_score": min(row["technical_context_score"] for row in scored),
                      "maximum_score": max(row["technical_context_score"] for row in scored),
                      "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
