from __future__ import annotations

import argparse
import json
from pathlib import Path

from alientai_v2.features.option_chain_features import option_chain_features
from alientai_v2.research.historical_call_evaluator import chain_path, load_chain


def read_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--chains", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows, missing = [], 0
    for event in read_jsonl(args.events):
        symbol, day = str(event.get("symbol") or "").upper(), str(event.get("market_date") or "")
        path = chain_path(args.chains, symbol, day)
        if not path.exists():
            missing += 1
            continue
        features = option_chain_features(load_chain(path), float(event.get("close") or 0))
        rows.append({
            "symbol": symbol, "market_date": day, "study_role": event.get("study_role"),
            "label_forward_return_5d_pct": event.get("label_forward_return_5d_pct"), **features,
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({"status": "complete", "rows": len(rows), "missing": missing, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
