from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from alientai_v2.research.matched_winner_study import build_matched_study, feature_contrasts, study_summary


ROOT = Path(__file__).resolve().parent


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a matched pre-move winner event study.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data_v2" / "rcef_research" / "matched_winner_study.jsonl")
    parser.add_argument("--winner-return-pct", type=float, default=5.0)
    parser.add_argument("--maximum-control-return-pct", type=float, default=1.0)
    parser.add_argument("--controls-per-winner", type=int, default=5)
    parser.add_argument("--minimum-calendar-gap-days", type=int, default=9)
    parser.add_argument("--summary-output", type=Path)
    args = parser.parse_args()
    result = build_matched_study(
        read_jsonl(args.input), winner_return_pct=args.winner_return_pct,
        maximum_control_return_pct=args.maximum_control_return_pct,
        controls_per_winner=args.controls_per_winner,
        minimum_calendar_gap_days=args.minimum_calendar_gap_days,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in result:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    summary = study_summary(result)
    summary["feature_contrasts"] = feature_contrasts(result)
    summary["output"] = str(args.output)
    summary_path = args.summary_output or args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary["summary_output"] = str(summary_path)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
