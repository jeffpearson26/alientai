from __future__ import annotations

"""Describe feature distributions before matched exceptional winners and controls."""

import argparse
import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping


DEFAULT_FEATURES = (
    "technical_rsi_2", "technical_atr14_pct", "technical_relative_volume_10_vs_20",
    "technical_volatility_compression_ratio", "news_article_count", "news_weighted_sentiment",
    "option_put_call_volume_ratio", "option_put_call_open_interest_ratio",
    "option_volume_open_interest_ratio", "option_near_money_call_iv", "option_near_money_put_iv",
)


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def precursor_profile(rows: Iterable[Mapping[str, Any]], features: Iterable[str] = DEFAULT_FEATURES) -> list[dict[str, Any]]:
    names = list(features)
    groups = {0: {name: [] for name in names}, 1: {name: [] for name in names}}
    for row in rows:
        group = int(row.get("study_label") or 0)
        if group not in groups:
            continue
        for name in names:
            try:
                value = float(row.get(name))
            except (TypeError, ValueError):
                continue
            if math.isfinite(value):
                groups[group][name].append(value)
    output = []
    for name in names:
        winners, controls = groups[1][name], groups[0][name]
        if winners and controls:
            winner_median, control_median = median(winners), median(controls)
            output.append({
                "feature": name, "winner_count": len(winners), "control_count": len(controls),
                "winner_median": round(winner_median, 6), "control_median": round(control_median, 6),
                "median_difference": round(winner_median - control_median, 6),
            })
    return sorted(output, key=lambda item: abs(float(item["median_difference"])), reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {"status": "complete", "research_only": True,
              "warning": "Matched case-control descriptive differences are hypotheses, not predictive effects or trading rules.",
              "features": precursor_profile(read_jsonl(args.input))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "features": len(report["features"]), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
