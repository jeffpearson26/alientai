from __future__ import annotations

"""Research-only outcome evaluation for leakage-safe unusual call activity."""

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from alientai_v2.research.unusual_call_activity import unusual_call_features
from alientai_v2.research.rare_signal_gate import evaluate_rare_signal_gate
from evaluate_matched_winner_full_universe import selection_metrics


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def key(row: Mapping[str, Any]) -> tuple[str, str]:
    return str(row.get("symbol") or "").upper(), str(row.get("market_date") or "")


def join_option_outcomes(base_rows: Iterable[Mapping[str, Any]], option_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    base = {key(row): row for row in base_rows}
    output = []
    for feature in unusual_call_features(option_rows):
        row = base.get(key(feature))
        if row is not None:
            output.append({**row, **feature})
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rows", type=Path, required=True)
    parser.add_argument("--option-features", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()
    rows = join_option_outcomes(read_jsonl(args.base_rows), read_jsonl(args.option_features))
    selected = [row for row in rows if row.get("call_volume_unusual")]
    unusual_metrics = selection_metrics(selected, args.round_trip_cost_pct)
    natural_metrics = selection_metrics(rows, args.round_trip_cost_pct)
    report = {"status": "complete", "research_only": True, "execution_enabled": False,
              "warning": "Historical public-data association only; unusual activity does not establish cause or private information.",
              "rows": len(rows), "unusual_signal_metrics": unusual_metrics,
              "unusual_signal_gate": evaluate_rare_signal_gate(unusual_metrics),
              "natural_universe_metrics": natural_metrics}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
