from __future__ import annotations

"""Evaluate a matched-trained options model on a separate natural-universe panel."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import lightgbm as lgb

from evaluate_matched_winner_full_universe import build_matrix, selection_metrics
from alientai_v2.research.rare_signal_gate import evaluate_rare_signal_gate


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def option_key(row: Mapping[str, Any]) -> tuple[str, str]:
    return str(row.get("symbol") or "").upper(), str(row.get("market_date") or "")


def join_options(base_rows: Iterable[Mapping[str, Any]], option_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    options = {option_key(row): row for row in option_rows}
    output = []
    for row in base_rows:
        matched = options.get(option_key(row))
        if matched is None:
            continue
        output.append({**row, **{name: value for name, value in matched.items() if name not in {"symbol", "market_date"}}})
    return output


def daily_top(rows: Sequence[Mapping[str, Any]], per_day: int, hold_calendar_days: int = 5) -> list[Mapping[str, Any]]:
    by_day: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_day[str(row["market_date"])].append(row)
    latest_exit: dict[str, str] = {}
    selected = []
    for day in sorted(by_day):
        for row in sorted(by_day[day], key=lambda item: -float(item["raw_score"]))[:per_day]:
            symbol = str(row["symbol"])
            # ISO dates compare lexically; the runner's five-day target is a
            # conservative hold boundary supplied by future_market_date.
            if day < latest_exit.get(symbol, ""):
                continue
            selected.append(row)
            latest_exit[symbol] = str(row.get("future_market_date") or day)
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rows", type=Path, required=True)
    parser.add_argument("--option-features", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()
    rows = join_options(read_jsonl(args.base_rows), read_jsonl(args.option_features))
    if not rows:
        raise ValueError("no natural-universe rows matched option features")
    model = lgb.Booster(model_file=str(args.model))
    scores = model.predict(build_matrix(rows, model.feature_name()))
    scored = [{**row, "raw_score": float(score)} for row, score in zip(rows, scores)]
    daily_reports = []
    for count in (1, 3, 5):
        metrics = selection_metrics(daily_top(scored, count), args.round_trip_cost_pct)
        daily_reports.append({"per_day": count, **metrics, "rare_signal_gate": evaluate_rare_signal_gate(metrics)})
    report = {"status": "complete", "research_only": True, "execution_enabled": False,
              "warning": "This is historical natural-universe ranking evaluation, not a prospective result.",
              "rows": len(scored), "round_trip_cost_pct": args.round_trip_cost_pct,
              "daily_top": daily_reports}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
