from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from alientai_v2.research.insider_event_evaluator import evaluate_rows


ROOT = Path(__file__).resolve().parent


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "data_v2" / "rcef_research" / "insider_pilot_rows.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "data_v2" / "rcef_research" / "insider_event_scorecard.json")
    parser.add_argument("--horizon-trading-days", type=int, default=5)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.25)
    args = parser.parse_args()
    result = evaluate_rows(
        read_jsonl(args.input), horizon_trading_days=args.horizon_trading_days,
        round_trip_cost_pct=args.round_trip_cost_pct,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
